'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';

// ============ TYPES ============

interface Skill {
  id: number;
  name: string;
  category: string;
}

interface StaffSkillEntry {
  skill_id: number;
  skill_name: string;
  level: number; // 1-5
  last_assessed: string;
}

interface StaffMember {
  id: number;
  name: string;
  department: string;
  role: string;
  avatar_url?: string;
  skills: StaffSkillEntry[];
}

interface SkillsResponse {
  staff: StaffMember[];
  skills: Skill[];
  departments: string[];
  skill_categories: string[];
}

interface GapAnalysisItem {
  skill_name: string;
  category: string;
  avg_level: number;
  staff_trained: number;
  total_staff: number;
  coverage_pct: number;
  severity: 'critical' | 'high' | 'medium' | 'low';
}

// ============ HELPERS ============

const levelColor = (level: number): string => {
  switch (level) {
    case 1: return 'bg-red-500 text-white';
    case 2: return 'bg-orange-400 text-white';
    case 3: return 'bg-yellow-400 text-gray-900';
    case 4: return 'bg-lime-500 text-white';
    case 5: return 'bg-green-600 text-white';
    default: return 'bg-gray-100 text-gray-400';
  }
};

const levelLabel = (level: number): string => {
  switch (level) {
    case 1: return 'Novice';
    case 2: return 'Beginner';
    case 3: return 'Competent';
    case 4: return 'Proficient';
    case 5: return 'Expert';
    default: return 'Unrated';
  }
};

const severityColor = (severity: string): string => {
  switch (severity) {
    case 'critical': return 'bg-red-50 border-red-200 text-red-800';
    case 'high': return 'bg-orange-50 border-orange-200 text-orange-800';
    case 'medium': return 'bg-yellow-50 border-yellow-200 text-yellow-800';
    case 'low': return 'bg-green-50 border-green-200 text-green-800';
    default: return 'bg-gray-50 border-gray-200 text-gray-800';
  }
};

// ============ COMPONENT ============

export default function StaffSkillsPage() {
  const [data, setData] = useState<SkillsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState<string | null>(null);

  // Filters
  const [filterDepartment, setFilterDepartment] = useState('all');
  const [filterCategory, setFilterCategory] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Edit state
  const [editCell, setEditCell] = useState<{ staffId: number; skillName: string } | null>(null);

  // View
  const [activeTab, setActiveTab] = useState<'matrix' | 'gaps' | 'performers'>('matrix');

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.get<SkillsResponse>('/staff/skills?venue_id=1');
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load skills data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const updateSkillLevel = async (staffId: number, skillName: string, level: number) => {
    setSaving(`${staffId}-${skillName}`);
    try {
      await api.put(`/staff/skills/${staffId}`, { skill_name: skillName, level });
      setData((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          staff: prev.staff.map((s) => {
            if (s.id !== staffId) return s;
            const existingIdx = s.skills.findIndex((sk) => sk.skill_name === skillName);
            if (existingIdx >= 0) {
              const updatedSkills = [...s.skills];
              updatedSkills[existingIdx] = {
                ...updatedSkills[existingIdx],
                level,
                last_assessed: new Date().toISOString(),
              };
              return { ...s, skills: updatedSkills };
            }
            return {
              ...s,
              skills: [
                ...s.skills,
                { skill_id: 0, skill_name: skillName, level, last_assessed: new Date().toISOString() },
              ],
            };
          }),
        };
      });
      setEditCell(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update skill');
    } finally {
      setSaving(null);
    }
  };

  // Filtered data
  const filteredStaff =
    data?.staff.filter((s) => {
      const matchesDept = filterDepartment === 'all' || s.department === filterDepartment;
      const matchesSearch =
        !searchQuery || s.name.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesDept && matchesSearch;
    }) || [];

  const filteredSkills =
    data?.skills.filter((s) => filterCategory === 'all' || s.category === filterCategory) || [];

  const getLevel = (staff: StaffMember, skillName: string): number => {
    return staff.skills.find((s) => s.skill_name === skillName)?.level ?? 0;
  };

  // Summary stats
  const allLevels = filteredStaff.flatMap((s) => s.skills.map((sk) => sk.level));
  const avgSkillLevel =
    allLevels.length > 0 ? (allLevels.reduce((a, b) => a + b, 0) / allLevels.length).toFixed(1) : '0';
  const totalTrainingGaps = filteredStaff.reduce(
    (count, s) => count + filteredSkills.filter((sk) => getLevel(s, sk.name) === 0).length,
    0
  );

  // Top performers: highest average skill level
  const performerStats = filteredStaff
    .map((s) => {
      const levels = filteredSkills.map((sk) => getLevel(s, sk.name)).filter((l) => l > 0);
      const avg = levels.length > 0 ? levels.reduce((a, b) => a + b, 0) / levels.length : 0;
      const skillCount = levels.length;
      return { ...s, avg_level: Math.round(avg * 10) / 10, skill_count: skillCount };
    })
    .sort((a, b) => b.avg_level - a.avg_level);

  // Gap analysis
  const gapAnalysis: GapAnalysisItem[] = filteredSkills
    .map((skill) => {
      const staffWithSkill = filteredStaff.filter((s) => getLevel(s, skill.name) > 0);
      const totalStaff = filteredStaff.length;
      const avgLevel =
        staffWithSkill.length > 0
          ? staffWithSkill.reduce((sum, s) => sum + getLevel(s, skill.name), 0) / staffWithSkill.length
          : 0;
      const coverage = totalStaff > 0 ? staffWithSkill.length / totalStaff : 0;

      let severity: GapAnalysisItem['severity'] = 'low';
      if (coverage < 0.25 || avgLevel < 2) severity = 'critical';
      else if (coverage < 0.4 || avgLevel < 2.5) severity = 'high';
      else if (coverage < 0.6 || avgLevel < 3) severity = 'medium';

      return {
        skill_name: skill.name,
        category: skill.category,
        avg_level: Math.round(avgLevel * 10) / 10,
        staff_trained: staffWithSkill.length,
        total_staff: totalStaff,
        coverage_pct: Math.round(coverage * 100),
        severity,
      };
    })
    .sort((a, b) => {
      const order = { critical: 0, high: 1, medium: 2, low: 3 };
      return order[a.severity] - order[b.severity];
    });

  // ---- Loading ----
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-500">Loading skills data...</p>
        </div>
      </div>
    );
  }

  // ---- Error (full page) ----
  if (error && !data) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Failed to Load Skills</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button onClick={loadData} className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white p-6">
      <div className="max-w-full mx-auto">
        {/* Header */}
        <div className="flex items-center gap-4 mb-6">
          <Link href="/staff" className="p-2 rounded-lg hover:bg-gray-100 transition-colors">
            <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-gray-900">Staff Skills & Training</h1>
            <p className="text-gray-500 mt-1">Track proficiency levels and identify training gaps</p>
          </div>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-blue-50 p-4 rounded-xl border border-blue-100">
            <p className="text-xs text-blue-600 font-medium uppercase tracking-wide">Avg Skill Level</p>
            <p className="text-3xl font-bold text-blue-700 mt-1">{avgSkillLevel}<span className="text-lg text-blue-400">/5</span></p>
          </div>
          <div className="bg-red-50 p-4 rounded-xl border border-red-100">
            <p className="text-xs text-red-600 font-medium uppercase tracking-wide">Training Gaps</p>
            <p className="text-3xl font-bold text-red-700 mt-1">{totalTrainingGaps}</p>
          </div>
          <div className="bg-green-50 p-4 rounded-xl border border-green-100">
            <p className="text-xs text-green-600 font-medium uppercase tracking-wide">Top Performer</p>
            <p className="text-lg font-bold text-green-700 mt-1 truncate">
              {performerStats[0]?.name || 'N/A'}
            </p>
            <p className="text-sm text-green-500">{performerStats[0]?.avg_level || 0}/5 avg</p>
          </div>
          <div className="bg-purple-50 p-4 rounded-xl border border-purple-100">
            <p className="text-xs text-purple-600 font-medium uppercase tracking-wide">Staff Tracked</p>
            <p className="text-3xl font-bold text-purple-700 mt-1">{filteredStaff.length}</p>
          </div>
        </div>

        {/* Filters & Search */}
        <div className="flex flex-col md:flex-row gap-3 mb-6">
          <input
            type="text"
            placeholder="Search staff..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 md:w-64"
          />
          <select
            value={filterDepartment}
            onChange={(e) => setFilterDepartment(e.target.value)}
            className="px-4 py-2 border border-gray-200 rounded-lg bg-white text-gray-700"
          >
            <option value="all">All Departments</option>
            {data?.departments.map((dept) => (
              <option key={dept} value={dept}>{dept}</option>
            ))}
          </select>
          <select
            value={filterCategory}
            onChange={(e) => setFilterCategory(e.target.value)}
            className="px-4 py-2 border border-gray-200 rounded-lg bg-white text-gray-700"
          >
            <option value="all">All Skill Categories</option>
            {data?.skill_categories.map((cat) => (
              <option key={cat} value={cat}>{cat}</option>
            ))}
          </select>
          <div className="flex gap-1 bg-gray-100 rounded-lg p-1 ml-auto">
            {(['matrix', 'gaps', 'performers'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors capitalize ${
                  activeTab === tab ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                {tab === 'gaps' ? 'Gap Analysis' : tab === 'performers' ? 'Top Performers' : 'Matrix'}
              </button>
            ))}
          </div>
        </div>

        {/* Inline error */}
        {error && data && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{error}</div>
        )}

        {/* Legend */}
        {activeTab === 'matrix' && (
          <div className="flex flex-wrap gap-2 mb-4 p-3 bg-gray-50 rounded-lg border border-gray-200">
            <span className="text-xs font-medium text-gray-500 mr-2 self-center">Skill Levels:</span>
            {[1, 2, 3, 4, 5].map((level) => (
              <span key={level} className={`px-2.5 py-1 rounded-full text-xs font-medium ${levelColor(level)}`}>
                {level} - {levelLabel(level)}
              </span>
            ))}
            <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-400">
              0 - Not Assessed
            </span>
          </div>
        )}

        {/* Matrix Tab */}
        {activeTab === 'matrix' && (
          <div className="overflow-x-auto rounded-xl border border-gray-200">
            <table className="min-w-full border-collapse">
              <thead>
                <tr className="bg-gray-50">
                  <th className="sticky left-0 z-10 bg-gray-50 px-4 py-3 text-left text-sm font-semibold text-gray-700 border-b border-r border-gray-200 min-w-[200px]">
                    Staff Member
                  </th>
                  {filteredSkills.map((skill) => (
                    <th
                      key={skill.id}
                      className="px-2 py-3 text-center text-xs font-semibold text-gray-700 border-b border-gray-200 min-w-[85px]"
                      title={`${skill.category}: ${skill.name}`}
                    >
                      <div className="truncate">{skill.name}</div>
                      <div className="text-gray-400 font-normal text-[10px] mt-0.5">{skill.category}</div>
                    </th>
                  ))}
                  <th className="px-3 py-3 text-center text-xs font-semibold text-gray-700 border-b border-l border-gray-200 min-w-[70px]">
                    Avg
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredStaff.map((member, rowIdx) => {
                  const memberLevels = filteredSkills.map((sk) => getLevel(member, sk.name)).filter((l) => l > 0);
                  const memberAvg =
                    memberLevels.length > 0
                      ? (memberLevels.reduce((a, b) => a + b, 0) / memberLevels.length).toFixed(1)
                      : '-';
                  return (
                    <tr key={member.id} className={rowIdx % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'}>
                      <td className="sticky left-0 z-10 px-4 py-3 border-b border-r border-gray-200 bg-inherit">
                        <div className="font-medium text-gray-900">{member.name}</div>
                        <div className="text-xs text-gray-500">
                          {member.department} &middot; {member.role}
                        </div>
                      </td>
                      {filteredSkills.map((skill) => {
                        const level = getLevel(member, skill.name);
                        const isEditing =
                          editCell?.staffId === member.id && editCell?.skillName === skill.name;
                        const isSaving = saving === `${member.id}-${skill.name}`;

                        return (
                          <td key={skill.id} className="px-1 py-1 border-b border-gray-200 text-center">
                            {isEditing ? (
                              <div className="flex items-center justify-center gap-0.5">
                                {[0, 1, 2, 3, 4, 5].map((v) => (
                                  <button
                                    key={v}
                                    onClick={() => updateSkillLevel(member.id, skill.name, v)}
                                    disabled={isSaving}
                                    className={`w-6 h-6 rounded text-xs font-bold transition-colors ${
                                      v === level ? 'ring-2 ring-blue-500 ' : ''
                                    }${v === 0 ? 'bg-gray-200 text-gray-500 hover:bg-gray-300' : levelColor(v) + ' hover:opacity-80'}`}
                                  >
                                    {v}
                                  </button>
                                ))}
                              </div>
                            ) : (
                              <button
                                onClick={() => setEditCell({ staffId: member.id, skillName: skill.name })}
                                className={`w-10 h-10 rounded-lg text-sm font-bold transition-all hover:scale-110 ${
                                  level === 0 ? 'bg-gray-100 text-gray-400 hover:bg-gray-200' : levelColor(level)
                                }`}
                                title={`${member.name}: ${skill.name} - ${levelLabel(level)} (${level})`}
                              >
                                {level || '-'}
                              </button>
                            )}
                          </td>
                        );
                      })}
                      <td className="px-3 py-3 border-b border-l border-gray-200 text-center">
                        <span className="text-sm font-bold text-gray-700">{memberAvg}</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {filteredStaff.length === 0 && (
              <div className="text-center py-12 text-gray-500">
                <p>No staff members match your filters</p>
              </div>
            )}
          </div>
        )}

        {/* Gap Analysis Tab */}
        {activeTab === 'gaps' && (
          <div>
            <h2 className="text-xl font-bold text-gray-900 mb-2">Skill Gap Analysis</h2>
            <p className="text-gray-500 mb-6 text-sm">Skills with low coverage or proficiency that need training attention</p>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {gapAnalysis.map((gap) => (
                <div
                  key={gap.skill_name}
                  className={`rounded-xl border p-5 ${severityColor(gap.severity)}`}
                >
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="font-semibold text-base">{gap.skill_name}</h3>
                    <span className="px-2 py-0.5 rounded-full text-xs font-bold uppercase opacity-80">
                      {gap.severity}
                    </span>
                  </div>
                  <div className="text-sm opacity-70 mb-3">{gap.category}</div>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span>Coverage</span>
                      <span className="font-medium">
                        {gap.staff_trained}/{gap.total_staff} staff ({gap.coverage_pct}%)
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Avg Level</span>
                      <span className="font-medium">{gap.avg_level}/5</span>
                    </div>
                    {/* Progress bar */}
                    <div className="h-2 bg-white/50 rounded-full overflow-hidden mt-1">
                      <div
                        className="h-full rounded-full bg-current opacity-40 transition-all"
                        style={{ width: `${(gap.avg_level / 5) * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {gapAnalysis.length === 0 && (
              <div className="text-center py-12 text-gray-500">
                No skill gaps detected. Great coverage across the team!
              </div>
            )}
          </div>
        )}

        {/* Top Performers Tab */}
        {activeTab === 'performers' && (
          <div>
            <h2 className="text-xl font-bold text-gray-900 mb-2">Top Performers</h2>
            <p className="text-gray-500 mb-6 text-sm">Staff ranked by average skill proficiency</p>

            <div className="space-y-3">
              {performerStats.map((member, idx) => (
                <div
                  key={member.id}
                  className={`flex items-center gap-4 p-4 rounded-xl border ${
                    idx === 0
                      ? 'bg-yellow-50 border-yellow-200'
                      : idx === 1
                      ? 'bg-gray-50 border-gray-200'
                      : idx === 2
                      ? 'bg-orange-50 border-orange-200'
                      : 'bg-white border-gray-200'
                  }`}
                >
                  <div className="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center text-lg font-bold text-gray-600 flex-shrink-0">
                    {idx < 3 ? (
                      <span className={`${idx === 0 ? 'text-yellow-600' : idx === 1 ? 'text-gray-500' : 'text-orange-600'}`}>
                        {idx + 1}
                      </span>
                    ) : (
                      <span className="text-sm text-gray-400">{idx + 1}</span>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h4 className="font-semibold text-gray-900 truncate">{member.name}</h4>
                    <p className="text-sm text-gray-500">{member.department} &middot; {member.role}</p>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <div className="text-lg font-bold text-gray-900">{member.avg_level}<span className="text-sm text-gray-400">/5</span></div>
                    <div className="text-xs text-gray-500">{member.skill_count} skills</div>
                  </div>
                  {/* Mini skill bar */}
                  <div className="w-32 flex-shrink-0 hidden sm:block">
                    <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${
                          member.avg_level >= 4 ? 'bg-green-500' : member.avg_level >= 3 ? 'bg-yellow-400' : 'bg-red-400'
                        }`}
                        style={{ width: `${(member.avg_level / 5) * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {performerStats.length === 0 && (
              <div className="text-center py-12 text-gray-500">
                No staff data available.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
