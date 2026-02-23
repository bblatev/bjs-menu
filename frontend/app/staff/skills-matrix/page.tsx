'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';

// ── Types ───────────────────────────────────────────────────────────────────

interface Skill {
  id: number;
  name: string;
  category: string;
}

interface StaffSkill {
  skill_id: number;
  proficiency: number; // 1-5
}

interface StaffMember {
  id: number;
  name: string;
  role: string;
  skills: StaffSkill[];
}

interface SkillsMatrixData {
  staff: StaffMember[];
  skills: Skill[];
  skill_categories: string[];
}

interface GapAnalysisItem {
  skill_name: string;
  category: string;
  avg_proficiency: number;
  staff_with_skill: number;
  total_staff: number;
  gap_severity: 'low' | 'medium' | 'high' | 'critical';
}

// ── Helpers ─────────────────────────────────────────────────────────────────

const proficiencyColor = (level: number): string => {
  switch (level) {
    case 1: return 'bg-red-500 text-white';
    case 2: return 'bg-orange-400 text-white';
    case 3: return 'bg-yellow-400 text-gray-900';
    case 4: return 'bg-green-400 text-white';
    case 5: return 'bg-green-600 text-white';
    default: return 'bg-gray-100 text-gray-400';
  }
};

const proficiencyLabel = (level: number): string => {
  switch (level) {
    case 1: return 'Novice';
    case 2: return 'Beginner';
    case 3: return 'Competent';
    case 4: return 'Proficient';
    case 5: return 'Expert';
    default: return 'N/A';
  }
};

const gapColor = (severity: string): string => {
  switch (severity) {
    case 'critical': return 'bg-red-100 text-red-800 border-red-200';
    case 'high': return 'bg-orange-100 text-orange-800 border-orange-200';
    case 'medium': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    case 'low': return 'bg-green-100 text-green-800 border-green-200';
    default: return 'bg-gray-100 text-gray-800 border-gray-200';
  }
};

// ── Component ───────────────────────────────────────────────────────────────

export default function SkillsMatrixPage() {
  const [matrixData, setMatrixData] = useState<SkillsMatrixData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState<string | null>(null);
  const [filterCategory, setFilterCategory] = useState<string>('all');
  const [editCell, setEditCell] = useState<{ staffId: number; skillId: number } | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<SkillsMatrixData>('/staff/skills-matrix');
      setMatrixData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load skills matrix');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const updateProficiency = async (staffId: number, skillId: number, level: number) => {
    if (!matrixData) return;
    setSaving(`${staffId}-${skillId}`);
    try {
      await api.put(`/staff/skills-matrix/${staffId}`, { skill_id: skillId, proficiency: level });
      setMatrixData(prev => {
        if (!prev) return prev;
        return {
          ...prev,
          staff: prev.staff.map(s => {
            if (s.id !== staffId) return s;
            const existing = s.skills.find(sk => sk.skill_id === skillId);
            if (existing) {
              return { ...s, skills: s.skills.map(sk => sk.skill_id === skillId ? { ...sk, proficiency: level } : sk) };
            }
            return { ...s, skills: [...s.skills, { skill_id: skillId, proficiency: level }] };
          }),
        };
      });
      setEditCell(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update proficiency');
    } finally {
      setSaving(null);
    }
  };

  const getProficiency = (staff: StaffMember, skillId: number): number => {
    return staff.skills.find(s => s.skill_id === skillId)?.proficiency ?? 0;
  };

  const filteredSkills = matrixData?.skills.filter(
    s => filterCategory === 'all' || s.category === filterCategory
  ) ?? [];

  const gapAnalysis: GapAnalysisItem[] = filteredSkills.map(skill => {
    const staffWithSkill = matrixData?.staff.filter(s => getProficiency(s, skill.id) > 0) ?? [];
    const totalStaff = matrixData?.staff.length ?? 0;
    const avgProf = staffWithSkill.length > 0
      ? staffWithSkill.reduce((sum, s) => sum + getProficiency(s, skill.id), 0) / staffWithSkill.length
      : 0;

    let gap_severity: GapAnalysisItem['gap_severity'] = 'low';
    const coverage = totalStaff > 0 ? staffWithSkill.length / totalStaff : 0;
    if (coverage < 0.25 || avgProf < 2) gap_severity = 'critical';
    else if (coverage < 0.4 || avgProf < 2.5) gap_severity = 'high';
    else if (coverage < 0.6 || avgProf < 3) gap_severity = 'medium';

    return {
      skill_name: skill.name,
      category: skill.category,
      avg_proficiency: Math.round(avgProf * 10) / 10,
      staff_with_skill: staffWithSkill.length,
      total_staff: totalStaff,
      gap_severity,
    };
  }).sort((a, b) => {
    const order = { critical: 0, high: 1, medium: 2, low: 3 };
    return order[a.gap_severity] - order[b.gap_severity];
  });

  // ── Loading ───────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4" />
          <p className="text-gray-500">Loading skills matrix...</p>
        </div>
      </div>
    );
  }

  // ── Error ─────────────────────────────────────────────────────────────────

  if (error && !matrixData) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Failed to Load</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button onClick={loadData} className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
            Retry
          </button>
        </div>
      </div>
    );
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-white p-6">
      <div className="max-w-full mx-auto">
        {/* Header */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Skills Matrix</h1>
            <p className="text-gray-500 mt-1">Track team proficiency levels across all skills</p>
          </div>
          <div className="flex items-center gap-3">
            <select
              value={filterCategory}
              onChange={e => setFilterCategory(e.target.value)}
              className="px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg text-gray-700"
            >
              <option value="all">All Categories</option>
              {matrixData?.skill_categories.map(cat => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">
            {error}
          </div>
        )}

        {/* Legend */}
        <div className="flex flex-wrap gap-3 mb-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
          <span className="text-sm font-medium text-gray-600 mr-2">Proficiency:</span>
          {[1, 2, 3, 4, 5].map(level => (
            <span key={level} className={`px-3 py-1 rounded-full text-xs font-medium ${proficiencyColor(level)}`}>
              {level} - {proficiencyLabel(level)}
            </span>
          ))}
          <span className="px-3 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-400">
            0 - Not assessed
          </span>
        </div>

        {/* Matrix Grid */}
        <div className="overflow-x-auto mb-8">
          <table className="min-w-full border-collapse">
            <thead>
              <tr className="bg-gray-50">
                <th className="sticky left-0 z-10 bg-gray-50 px-4 py-3 text-left text-sm font-semibold text-gray-700 border-b border-r border-gray-200 min-w-[180px]">
                  Staff Member
                </th>
                {filteredSkills.map(skill => (
                  <th
                    key={skill.id}
                    className="px-3 py-3 text-center text-xs font-semibold text-gray-700 border-b border-gray-200 min-w-[90px]"
                    title={`${skill.category}: ${skill.name}`}
                  >
                    <div className="truncate">{skill.name}</div>
                    <div className="text-gray-400 font-normal text-[10px]">{skill.category}</div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {matrixData?.staff.map((member, rowIdx) => (
                <tr key={member.id} className={rowIdx % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'}>
                  <td className="sticky left-0 z-10 px-4 py-3 border-b border-r border-gray-200 bg-inherit">
                    <div className="font-medium text-gray-900">{member.name}</div>
                    <div className="text-xs text-gray-500">{member.role}</div>
                  </td>
                  {filteredSkills.map(skill => {
                    const level = getProficiency(member, skill.id);
                    const isEditing = editCell?.staffId === member.id && editCell?.skillId === skill.id;
                    const isSaving = saving === `${member.id}-${skill.id}`;

                    return (
                      <td
                        key={skill.id}
                        className="px-1 py-1 border-b border-gray-200 text-center"
                      >
                        {isEditing ? (
                          <div className="flex items-center justify-center gap-0.5">
                            {[0, 1, 2, 3, 4, 5].map(v => (
                              <button
                                key={v}
                                onClick={() => updateProficiency(member.id, skill.id, v)}
                                disabled={isSaving}
                                className={`w-6 h-6 rounded text-xs font-bold transition-colors ${
                                  v === level ? 'ring-2 ring-blue-500 ' : ''
                                }${v === 0 ? 'bg-gray-200 text-gray-500 hover:bg-gray-300' : proficiencyColor(v) + ' hover:opacity-80'}`}
                              >
                                {v}
                              </button>
                            ))}
                          </div>
                        ) : (
                          <button
                            onClick={() => setEditCell({ staffId: member.id, skillId: skill.id })}
                            className={`w-10 h-10 rounded-lg text-sm font-bold transition-all hover:scale-110 ${
                              level === 0 ? 'bg-gray-100 text-gray-400 hover:bg-gray-200' : proficiencyColor(level)
                            }`}
                            title={`${member.name}: ${skill.name} - ${proficiencyLabel(level)} (${level})`}
                          >
                            {level || '-'}
                          </button>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Gap Analysis Section */}
        <div className="mt-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Gap Analysis</h2>
          <p className="text-gray-500 mb-6">Skills with low coverage or proficiency that need attention</p>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {gapAnalysis.map(gap => (
              <div
                key={gap.skill_name}
                className={`rounded-lg border p-4 ${gapColor(gap.gap_severity)}`}
              >
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold">{gap.skill_name}</h3>
                  <span className="px-2 py-0.5 rounded-full text-xs font-bold uppercase">
                    {gap.gap_severity}
                  </span>
                </div>
                <div className="text-sm opacity-80">{gap.category}</div>
                <div className="mt-3 space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span>Coverage</span>
                    <span className="font-medium">{gap.staff_with_skill}/{gap.total_staff} staff</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Avg Proficiency</span>
                    <span className="font-medium">{gap.avg_proficiency}/5</span>
                  </div>
                  <div className="h-2 bg-white/50 rounded-full overflow-hidden mt-2">
                    <div
                      className="h-full rounded-full bg-current opacity-40"
                      style={{ width: `${(gap.avg_proficiency / 5) * 100}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>

          {gapAnalysis.length === 0 && (
            <div className="text-center py-12 text-gray-500">
              No skill gaps found -- great coverage across the team.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
