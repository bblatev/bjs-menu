'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';

import { api } from '@/lib/api';

/** Escape HTML special characters to prevent XSS in template preview */
function escapeHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/** Validate and sanitize URL - only allow http/https/mailto protocols */
function sanitizeUrl(url: string): string {
  if (!url) return '#';
  try {
    const parsed = new URL(url);
    if (['http:', 'https:', 'mailto:'].includes(parsed.protocol)) {
      return parsed.href;
    }
  } catch {
    // not a valid URL
  }
  return '#';
}

interface TemplateBlock {
  block_id: string;
  type: string;
  content: Record<string, any>;
  styles: Record<string, string>;
  order: number;
}

interface EmailTemplate {
  template_id: string;
  name: string;
  subject: string;
  preview_text: string;
  blocks: TemplateBlock[];
  global_styles: Record<string, string>;
}

const BLOCK_TYPES = [
  { id: 'header', name: 'Header', icon: '🏷️', description: 'Logo and title' },
  { id: 'text', name: 'Text', icon: '📝', description: 'Paragraph text' },
  { id: 'image', name: 'Image', icon: '🖼️', description: 'Image with alt text' },
  { id: 'button', name: 'Button', icon: '🔘', description: 'Call-to-action' },
  { id: 'divider', name: 'Divider', icon: '➖', description: 'Horizontal line' },
  { id: 'coupon', name: 'Coupon', icon: '🎟️', description: 'Discount code' },
  { id: 'footer', name: 'Footer', icon: '📋', description: 'Address & unsubscribe' },
];

const VARIABLES = [
  { name: 'customer_name', label: 'Customer Name' },
  { name: 'customer_email', label: 'Customer Email' },
  { name: 'venue_name', label: 'Restaurant Name' },
  { name: 'venue_address', label: 'Restaurant Address' },
  { name: 'venue_phone', label: 'Restaurant Phone' },
  { name: 'order_url', label: 'Order URL' },
  { name: 'reservation_url', label: 'Reservation URL' },
  { name: 'unsubscribe_url', label: 'Unsubscribe URL' },
];

export default function TemplateBuilderPage() {
  const [template, setTemplate] = useState<EmailTemplate>({
    template_id: '',
    name: 'New Template',
    subject: 'Your Subject Line',
    preview_text: 'Preview text here...',
    blocks: [],
    global_styles: {},
  });
  const [selectedBlock, setSelectedBlock] = useState<string | null>(null);
  const [previewHtml, setPreviewHtml] = useState<string>('');
  const [saving, setSaving] = useState(false);
  const [, setLoading] = useState(true);
  const [, setError] = useState<string | null>(null);
  const [templates, setTemplates] = useState<EmailTemplate[]>([]);
  const [showTemplateList, setShowTemplateList] = useState(false);

  useEffect(() => {
    loadTemplates();
  }, []);

  useEffect(() => {
    const generatePreview = async () => {
      if (!template.template_id && template.blocks.length === 0) {
        setPreviewHtml('<div style="padding: 40px; text-align: center; color: #666;">Add blocks to see preview</div>');
        return;
      }

      // Generate simple preview HTML
      let html = `
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background: white; padding: 20px;">
      `;

      for (const block of template.blocks.sort((a, b) => a.order - b.order)) {
        html += renderBlockHtml(block);
      }

      html += '</div>';
      setPreviewHtml(html);
    };
    generatePreview();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [template.blocks]);

  const loadTemplates = async () => {
    setLoading(true);
    setError(null);
    try {
      const data: any = await api.get('/email-campaigns/templates');
            setTemplates(data);
    } catch (err) {
      console.error('Error loading templates:', err);
      setError('Failed to load email templates. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const renderBlockHtml = (block: TemplateBlock): string => {
    const content = block.content;

    switch (block.type) {
      case 'header':
        return `
          <div style="text-align: center; padding: 20px 0; border-bottom: 1px solid #eee;">
            ${content.logo_url ? `<img src="${sanitizeUrl(content.logo_url)}" alt="Logo" style="max-width: 150px;">` : ''}
            <h1 style="margin: 10px 0; color: #333;">${escapeHtml(content.title || 'Header Title')}</h1>
          </div>
        `;
      case 'text':
        return `
          <div style="padding: 15px 0; color: #444; line-height: 1.6;">
            ${escapeHtml(content.text || 'Your text content here...').replace(/\n/g, '<br>')}
          </div>
        `;
      case 'image':
        return `
          <div style="text-align: center; padding: 15px 0;">
            <img src="${sanitizeUrl(content.url || 'https://via.placeholder.com/600x300')}" alt="${escapeHtml(content.alt || 'Image')}" style="max-width: 100%; border-radius: 8px;">
          </div>
        `;
      case 'button':
        return `
          <div style="text-align: center; padding: 20px 0;">
            <a href="${sanitizeUrl(content.url || '#')}" style="display: inline-block; padding: 12px 30px; background: #3b82f6; color: white; text-decoration: none; border-radius: 6px; font-weight: bold;">
              ${escapeHtml(content.text || 'Click Here')}
            </a>
          </div>
        `;
      case 'divider':
        return `<hr style="border: none; border-top: 1px solid #e5e7eb; margin: 20px 0;">`;
      case 'coupon':
        return `
          <div style="border: 2px dashed #f59e0b; padding: 20px; text-align: center; background: #fef3c7; border-radius: 8px; margin: 15px 0;">
            <div style="font-size: 24px; font-weight: bold; color: #f59e0b;">${escapeHtml(content.discount || '10% OFF')}</div>
            <div style="margin: 10px 0; color: #666;">${escapeHtml(content.description || 'Your next order')}</div>
            <div style="font-size: 20px; font-weight: bold; letter-spacing: 3px; background: white; padding: 10px; border-radius: 4px; margin: 10px 0;">
              ${escapeHtml(content.code || 'SAVE10')}
            </div>
            <div style="font-size: 12px; color: #888;">Expires: ${escapeHtml(content.expires || '12/31/2026')}</div>
          </div>
        `;
      case 'footer':
        return `
          <div style="text-align: center; padding: 20px 0; color: #888; font-size: 12px; border-top: 1px solid #eee; margin-top: 20px;">
            <p>${escapeHtml(content.address || '123 Restaurant St, City')}</p>
            <p>${escapeHtml(content.phone || '(555) 123-4567')}</p>
            <p><a href="${sanitizeUrl(content.unsubscribe_url || '#')}" style="color: #888;">Unsubscribe</a></p>
          </div>
        `;
      default:
        return '';
    }
  };

  const addBlock = (type: string) => {
    const newBlock: TemplateBlock = {
      block_id: `b${Date.now()}`,
      type,
      content: getDefaultContent(type),
      styles: {},
      order: template.blocks.length,
    };

    setTemplate({
      ...template,
      blocks: [...template.blocks, newBlock],
    });
    setSelectedBlock(newBlock.block_id);
  };

  const getDefaultContent = (type: string): Record<string, any> => {
    switch (type) {
      case 'header':
        return { logo_url: '', title: 'Welcome!' };
      case 'text':
        return { text: 'Enter your text here...' };
      case 'image':
        return { url: '', alt: 'Image' };
      case 'button':
        return { text: 'Click Here', url: '#' };
      case 'coupon':
        return { code: 'SAVE10', discount: '10% OFF', description: 'Your next order', expires: '' };
      case 'footer':
        return { address: '{{venue_address}}', phone: '{{venue_phone}}', unsubscribe_url: '{{unsubscribe_url}}' };
      default:
        return {};
    }
  };

  const updateBlock = (blockId: string, content: Record<string, any>) => {
    setTemplate({
      ...template,
      blocks: template.blocks.map(b =>
        b.block_id === blockId ? { ...b, content } : b
      ),
    });
  };

  const deleteBlock = (blockId: string) => {
    setTemplate({
      ...template,
      blocks: template.blocks.filter(b => b.block_id !== blockId),
    });
    if (selectedBlock === blockId) {
      setSelectedBlock(null);
    }
  };

  const moveBlock = (blockId: string, direction: 'up' | 'down') => {
    const blocks = [...template.blocks].sort((a, b) => a.order - b.order);
    const index = blocks.findIndex(b => b.block_id === blockId);

    if (direction === 'up' && index > 0) {
      [blocks[index], blocks[index - 1]] = [blocks[index - 1], blocks[index]];
    } else if (direction === 'down' && index < blocks.length - 1) {
      [blocks[index], blocks[index + 1]] = [blocks[index + 1], blocks[index]];
    }

    setTemplate({
      ...template,
      blocks: blocks.map((b, i) => ({ ...b, order: i })),
    });
  };

  const saveTemplate = async () => {
    setSaving(true);
    try {
      const payload = {
        name: template.name,
        subject: template.subject,
        preview_text: template.preview_text,
        blocks: template.blocks,
        global_styles: template.global_styles,
      };

      let saved: any;
      if (template.template_id) {
        saved = await api.put(`/email-campaigns/templates/${template.template_id}`, payload);
      } else {
        saved = await api.post('/email-campaigns/templates', payload);
      }
      setTemplate({ ...template, template_id: saved.template_id });
      loadTemplates();
    } catch (error) {
      console.error('Error saving template:', error);
    } finally {
      setSaving(false);
    }
  };

  const loadTemplate = (t: EmailTemplate) => {
    setTemplate(t);
    setShowTemplateList(false);
    setSelectedBlock(null);
  };

  const newTemplate = () => {
    setTemplate({
      template_id: '',
      name: 'New Template',
      subject: 'Your Subject Line',
      preview_text: 'Preview text here...',
      blocks: [],
      global_styles: {},
    });
    setSelectedBlock(null);
  };

  const selectedBlockData = template.blocks.find(b => b.block_id === selectedBlock);

  return (
    <div className="h-screen flex flex-col bg-surface-50">
      {/* Header */}
      <div className="bg-white border-b border-surface-200 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/marketing/email" className="p-2 rounded-lg hover:bg-surface-100">
            <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <div>
            <input
              type="text"
              value={template.name}
              onChange={(e) => setTemplate({ ...template, name: e.target.value })}
              className="text-xl font-bold text-surface-900 bg-transparent border-none focus:outline-none focus:ring-2 focus:ring-amber-500 rounded px-2 -ml-2"
            />
            <div className="text-sm text-surface-500">Email Template Builder</div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowTemplateList(true)}
            className="px-4 py-2 text-surface-600 hover:bg-surface-100 rounded-lg"
          >
            Load Template
          </button>
          <button
            onClick={newTemplate}
            className="px-4 py-2 text-surface-600 hover:bg-surface-100 rounded-lg"
          >
            New
          </button>
          <button
            onClick={saveTemplate}
            disabled={saving}
            className="px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600 disabled:opacity-50 flex items-center gap-2"
          >
            {saving ? (
              <div className="w-4 h-4 border-2 border-gray-900 border-t-transparent rounded-full animate-spin" />
            ) : (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            )}
            Save
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Block Palette */}
        <div className="w-64 bg-white border-r border-surface-200 p-4 overflow-y-auto">
          <h3 className="font-semibold text-surface-900 mb-3">Add Blocks</h3>
          <div className="space-y-2">
            {BLOCK_TYPES.map((block) => (
              <button
                key={block.id}
                onClick={() => addBlock(block.id)}
                className="w-full p-3 bg-surface-50 rounded-lg hover:bg-surface-100 text-left flex items-center gap-3 transition-colors"
              >
                <span className="text-2xl">{block.icon}</span>
                <div>
                  <div className="font-medium text-surface-900">{block.name}</div>
                  <div className="text-xs text-surface-500">{block.description}</div>
                </div>
              </button>
            ))}
          </div>

          <div className="mt-6 pt-6 border-t border-surface-200">
            <h3 className="font-semibold text-surface-900 mb-3">Variables</h3>
            <div className="space-y-1">
              {VARIABLES.map((v) => (
                <div
                  key={v.name}
                  className="px-2 py-1 bg-surface-100 rounded text-xs font-mono cursor-pointer hover:bg-surface-200"
                  onClick={() => navigator.clipboard.writeText(`{{${v.name}}}`)}
                  title="Click to copy"
                >
                  {`{{${v.name}}}`}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Canvas */}
        <div className="flex-1 p-6 overflow-y-auto">
          <div className="max-w-2xl mx-auto">
            {/* Subject & Preview */}
            <div className="bg-white rounded-xl p-4 mb-4 border border-surface-200">
              <div className="mb-3">
                <label className="block text-sm font-medium text-surface-700 mb-1">Subject Line
                <input
                  type="text"
                  value={template.subject}
                  onChange={(e) => setTemplate({ ...template, subject: e.target.value })}
                  className="w-full px-3 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                />
                </label>
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">Preview Text
                <input
                  type="text"
                  value={template.preview_text}
                  onChange={(e) => setTemplate({ ...template, preview_text: e.target.value })}
                  className="w-full px-3 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                />
                </label>
              </div>
            </div>

            {/* Blocks */}
            <div className="space-y-2">
              {template.blocks.length === 0 ? (
                <div className="bg-white rounded-xl p-12 border-2 border-dashed border-surface-300 text-center">
                  <div className="text-4xl mb-4">📧</div>
                  <h3 className="font-semibold text-surface-900 mb-2">Start Building Your Template</h3>
                  <p className="text-surface-500">Click blocks from the left panel to add them</p>
                </div>
              ) : (
                template.blocks.sort((a, b) => a.order - b.order).map((block, index) => (
                  <motion.div
                    key={block.block_id}
                    layout
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`bg-white rounded-xl border-2 transition-colors ${
                      selectedBlock === block.block_id
                        ? 'border-amber-500'
                        : 'border-surface-200 hover:border-surface-300'
                    }`}
                  >
                    <div
                      className="p-4 cursor-pointer"
                      onClick={() => setSelectedBlock(block.block_id)}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="text-lg">
                            {BLOCK_TYPES.find(t => t.id === block.type)?.icon}
                          </span>
                          <span className="font-medium text-surface-900">
                            {BLOCK_TYPES.find(t => t.id === block.type)?.name}
                          </span>
                        </div>
                        <div className="flex items-center gap-1">
                          <button
                            onClick={(e) => { e.stopPropagation(); moveBlock(block.block_id, 'up'); }}
                            disabled={index === 0}
                            className="p-1 text-surface-400 hover:text-surface-600 disabled:opacity-30"
                          >
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                            </svg>
                          </button>
                          <button
                            onClick={(e) => { e.stopPropagation(); moveBlock(block.block_id, 'down'); }}
                            disabled={index === template.blocks.length - 1}
                            className="p-1 text-surface-400 hover:text-surface-600 disabled:opacity-30"
                          >
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                            </svg>
                          </button>
                          <button
                            onClick={(e) => { e.stopPropagation(); deleteBlock(block.block_id); }}
                            className="p-1 text-red-400 hover:text-red-600"
                          >
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        </div>
                      </div>
                      <div
                        className="text-sm text-surface-600 bg-surface-50 rounded-lg p-3"
                        dangerouslySetInnerHTML={{ __html: renderBlockHtml(block) }}
                      />
                    </div>
                  </motion.div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Properties Panel */}
        <div className="w-80 bg-white border-l border-surface-200 p-4 overflow-y-auto">
          {selectedBlockData ? (
            <>
              <h3 className="font-semibold text-surface-900 mb-4">
                {BLOCK_TYPES.find(t => t.id === selectedBlockData.type)?.name} Properties
              </h3>
              <div className="space-y-4">
                {selectedBlockData.type === 'header' && (
                  <>
                    <div>
                      <label className="block text-sm font-medium text-surface-700 mb-1">Logo URL
                      <input
                        type="text"
                        value={selectedBlockData.content.logo_url || ''}
                        onChange={(e) => updateBlock(selectedBlockData.block_id, { ...selectedBlockData.content, logo_url: e.target.value })}
                        className="w-full px-3 py-2 border border-surface-200 rounded-lg text-sm"
                        placeholder="https://..."
                      />
                      </label>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-surface-700 mb-1">Title
                      <input
                        type="text"
                        value={selectedBlockData.content.title || ''}
                        onChange={(e) => updateBlock(selectedBlockData.block_id, { ...selectedBlockData.content, title: e.target.value })}
                        className="w-full px-3 py-2 border border-surface-200 rounded-lg text-sm"
                      />
                      </label>
                    </div>
                  </>
                )}

                {selectedBlockData.type === 'text' && (
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">Content
                    <textarea
                      value={selectedBlockData.content.text || ''}
                      onChange={(e) => updateBlock(selectedBlockData.block_id, { ...selectedBlockData.content, text: e.target.value })}
                      rows={6}
                      className="w-full px-3 py-2 border border-surface-200 rounded-lg text-sm"
                    />
                    </label>
                  </div>
                )}

                {selectedBlockData.type === 'image' && (
                  <>
                    <div>
                      <label className="block text-sm font-medium text-surface-700 mb-1">Image URL
                      <input
                        type="text"
                        value={selectedBlockData.content.url || ''}
                        onChange={(e) => updateBlock(selectedBlockData.block_id, { ...selectedBlockData.content, url: e.target.value })}
                        className="w-full px-3 py-2 border border-surface-200 rounded-lg text-sm"
                        placeholder="https://..."
                      />
                      </label>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-surface-700 mb-1">Alt Text
                      <input
                        type="text"
                        value={selectedBlockData.content.alt || ''}
                        onChange={(e) => updateBlock(selectedBlockData.block_id, { ...selectedBlockData.content, alt: e.target.value })}
                        className="w-full px-3 py-2 border border-surface-200 rounded-lg text-sm"
                      />
                      </label>
                    </div>
                  </>
                )}

                {selectedBlockData.type === 'button' && (
                  <>
                    <div>
                      <label className="block text-sm font-medium text-surface-700 mb-1">Button Text
                      <input
                        type="text"
                        value={selectedBlockData.content.text || ''}
                        onChange={(e) => updateBlock(selectedBlockData.block_id, { ...selectedBlockData.content, text: e.target.value })}
                        className="w-full px-3 py-2 border border-surface-200 rounded-lg text-sm"
                      />
                      </label>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-surface-700 mb-1">Link URL
                      <input
                        type="text"
                        value={selectedBlockData.content.url || ''}
                        onChange={(e) => updateBlock(selectedBlockData.block_id, { ...selectedBlockData.content, url: e.target.value })}
                        className="w-full px-3 py-2 border border-surface-200 rounded-lg text-sm"
                        placeholder="https://..."
                      />
                      </label>
                    </div>
                  </>
                )}

                {selectedBlockData.type === 'coupon' && (
                  <>
                    <div>
                      <label className="block text-sm font-medium text-surface-700 mb-1">Coupon Code
                      <input
                        type="text"
                        value={selectedBlockData.content.code || ''}
                        onChange={(e) => updateBlock(selectedBlockData.block_id, { ...selectedBlockData.content, code: e.target.value })}
                        className="w-full px-3 py-2 border border-surface-200 rounded-lg text-sm font-mono"
                      />
                      </label>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-surface-700 mb-1">Discount
                      <input
                        type="text"
                        value={selectedBlockData.content.discount || ''}
                        onChange={(e) => updateBlock(selectedBlockData.block_id, { ...selectedBlockData.content, discount: e.target.value })}
                        className="w-full px-3 py-2 border border-surface-200 rounded-lg text-sm"
                        placeholder="e.g., 20% OFF"
                      />
                      </label>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-surface-700 mb-1">Description
                      <input
                        type="text"
                        value={selectedBlockData.content.description || ''}
                        onChange={(e) => updateBlock(selectedBlockData.block_id, { ...selectedBlockData.content, description: e.target.value })}
                        className="w-full px-3 py-2 border border-surface-200 rounded-lg text-sm"
                      />
                      </label>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-surface-700 mb-1">Expires
                      <input
                        type="text"
                        value={selectedBlockData.content.expires || ''}
                        onChange={(e) => updateBlock(selectedBlockData.block_id, { ...selectedBlockData.content, expires: e.target.value })}
                        className="w-full px-3 py-2 border border-surface-200 rounded-lg text-sm"
                        placeholder="e.g., 12/31/2026"
                      />
                      </label>
                    </div>
                  </>
                )}

                {selectedBlockData.type === 'footer' && (
                  <>
                    <div>
                      <label className="block text-sm font-medium text-surface-700 mb-1">Address
                      <input
                        type="text"
                        value={selectedBlockData.content.address || ''}
                        onChange={(e) => updateBlock(selectedBlockData.block_id, { ...selectedBlockData.content, address: e.target.value })}
                        className="w-full px-3 py-2 border border-surface-200 rounded-lg text-sm"
                      />
                      </label>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-surface-700 mb-1">Phone
                      <input
                        type="text"
                        value={selectedBlockData.content.phone || ''}
                        onChange={(e) => updateBlock(selectedBlockData.block_id, { ...selectedBlockData.content, phone: e.target.value })}
                        className="w-full px-3 py-2 border border-surface-200 rounded-lg text-sm"
                      />
                      </label>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-surface-700 mb-1">Unsubscribe URL
                      <input
                        type="text"
                        value={selectedBlockData.content.unsubscribe_url || ''}
                        onChange={(e) => updateBlock(selectedBlockData.block_id, { ...selectedBlockData.content, unsubscribe_url: e.target.value })}
                        className="w-full px-3 py-2 border border-surface-200 rounded-lg text-sm"
                      />
                      </label>
                    </div>
                  </>
                )}
              </div>
            </>
          ) : (
            <div className="text-center text-surface-500 py-12">
              <div className="text-4xl mb-4">👈</div>
              <p>Select a block to edit its properties</p>
            </div>
          )}

          {/* Preview Section */}
          <div className="mt-6 pt-6 border-t border-surface-200">
            <h3 className="font-semibold text-surface-900 mb-3">Live Preview</h3>
            <div
              className="bg-surface-100 rounded-lg overflow-hidden"
              style={{ maxHeight: '400px', overflowY: 'auto' }}
            >
              <div
                dangerouslySetInnerHTML={{ __html: previewHtml }}
                style={{ transform: 'scale(0.5)', transformOrigin: 'top left', width: '200%' }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Template List Modal */}
      <AnimatePresence>
        {showTemplateList && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden"
            >
              <div className="p-6 border-b border-surface-100 flex items-center justify-between">
                <h2 className="text-xl font-bold text-surface-900">Load Template</h2>
                <button
                  onClick={() => setShowTemplateList(false)}
                  className="p-2 text-surface-400 hover:text-surface-600"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <div className="p-6 overflow-y-auto max-h-[60vh]">
                {templates.length === 0 ? (
                  <div className="text-center py-12 text-surface-500">
                    No templates found. Create your first template!
                  </div>
                ) : (
                  <div className="grid grid-cols-2 gap-4">
                    {templates.map((t) => (
                      <button
                        key={t.template_id}
                        onClick={() => loadTemplate(t)}
                        className="p-4 border border-surface-200 rounded-xl text-left hover:border-amber-500 hover:bg-amber-50 transition-colors"
                      >
                        <h3 className="font-semibold text-surface-900 mb-1">{t.name}</h3>
                        <p className="text-sm text-surface-500 truncate">{t.subject}</p>
                        <p className="text-xs text-surface-400 mt-2">{t.blocks?.length || 0} blocks</p>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
