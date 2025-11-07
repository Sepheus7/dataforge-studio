/**
 * Schema editor for manual schema creation
 */

'use client';

import React, { useState } from 'react';
import { Plus, Trash2, Play, FileJson, AlertCircle } from 'lucide-react';
import { api } from '@/services/api';
import { useAppStore } from '@/lib/store';

interface Column {
  name: string;
  type: string;
  constraints?: string[];
}

interface Table {
  name: string;
  rows: number;
  columns: Column[];
}

const columnTypes = [
  'integer',
  'string',
  'email',
  'phone',
  'name',
  'address',
  'date',
  'datetime',
  'boolean',
  'float',
  'url',
  'uuid',
];

export default function SchemaView() {
  const [tables, setTables] = useState<Table[]>([
    {
      name: 'users',
      rows: 100,
      columns: [
        { name: 'id', type: 'integer', constraints: ['primary_key'] },
        { name: 'name', type: 'name' },
        { name: 'email', type: 'email' },
        { name: 'created_at', type: 'datetime' },
      ],
    },
  ]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const addJob = useAppStore((state) => state.addJob);

  const addTable = () => {
    setTables([
      ...tables,
      {
        name: `table_${tables.length + 1}`,
        rows: 100,
        columns: [{ name: 'id', type: 'integer', constraints: ['primary_key'] }],
      },
    ]);
  };

  const removeTable = (index: number) => {
    setTables(tables.filter((_, i) => i !== index));
  };

  const updateTable = (index: number, updates: Partial<Table>) => {
    const newTables = [...tables];
    newTables[index] = { ...newTables[index], ...updates };
    setTables(newTables);
  };

  const addColumn = (tableIndex: number) => {
    const newTables = [...tables];
    newTables[tableIndex].columns.push({
      name: `column_${newTables[tableIndex].columns.length + 1}`,
      type: 'string',
    });
    setTables(newTables);
  };

  const removeColumn = (tableIndex: number, columnIndex: number) => {
    const newTables = [...tables];
    newTables[tableIndex].columns = newTables[tableIndex].columns.filter(
      (_, i) => i !== columnIndex
    );
    setTables(newTables);
  };

  const updateColumn = (
    tableIndex: number,
    columnIndex: number,
    updates: Partial<Column>
  ) => {
    const newTables = [...tables];
    newTables[tableIndex].columns[columnIndex] = {
      ...newTables[tableIndex].columns[columnIndex],
      ...updates,
    };
    setTables(newTables);
  };

  const handleGenerate = async () => {
    setError(null);
    setIsGenerating(true);

    try {
      // Build schema object matching backend format
      const schema = {
        tables: tables.map((table) => ({
          name: table.name,
          rows: table.rows,
          columns: table.columns.map((col) => ({
            name: col.name,
            type: col.type,
            constraints: col.constraints || [],
          })),
        })),
      };

      // Generate from schema
      const response = await api.generateFromSchema({ schema });

      // Add job to store
      addJob({
        job_id: response.job_id,
        status: response.status as any,
        created_at: new Date().toISOString(),
      });

      // Show success and switch to jobs view
      alert('Data generation started! Check the Jobs tab for progress.');
    } catch (err: any) {
      setError(err.message || 'Failed to start generation');
    } finally {
      setIsGenerating(false);
    }
  };

  const exportSchema = () => {
    const schema = {
      tables: tables.map((table) => ({
        name: table.name,
        rows: table.rows,
        columns: table.columns,
      })),
    };

    const blob = new Blob([JSON.stringify(schema, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'schema.json';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Schema Editor</h1>
          <p className="text-sm text-gray-600 mt-1">
            Design your database schema manually
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={exportSchema}
            className="flex items-center space-x-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <FileJson className="w-4 h-4" />
            <span>Export JSON</span>
          </button>
          <button
            onClick={handleGenerate}
            disabled={isGenerating || tables.length === 0}
            className="flex items-center space-x-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 transition-colors"
          >
            <Play className="w-4 h-4" />
            <span>{isGenerating ? 'Generating...' : 'Generate Data'}</span>
          </button>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="bg-red-50 border-b border-red-200 px-6 py-3">
          <div className="flex items-center space-x-2 text-red-800">
            <AlertCircle className="w-5 h-5" />
            <span className="text-sm">{error}</span>
          </div>
        </div>
      )}

      {/* Schema Editor */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-5xl mx-auto space-y-6">
          {tables.map((table, tableIndex) => (
            <div key={tableIndex} className="bg-white rounded-lg border border-gray-200 p-6">
              {/* Table Header */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-4 flex-1">
                  <input
                    type="text"
                    value={table.name}
                    onChange={(e) => updateTable(tableIndex, { name: e.target.value })}
                    className="text-lg font-semibold border-b border-transparent hover:border-gray-300 focus:border-primary-500 outline-none px-2 py-1"
                    placeholder="Table name"
                  />
                  <input
                    type="number"
                    value={table.rows}
                    onChange={(e) =>
                      updateTable(tableIndex, { rows: parseInt(e.target.value) || 0 })
                    }
                    className="w-24 px-3 py-1 border border-gray-300 rounded text-sm"
                    min="1"
                    placeholder="Rows"
                  />
                  <span className="text-sm text-gray-600">rows</span>
                </div>
                <button
                  onClick={() => removeTable(tableIndex)}
                  className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                >
                  <Trash2 className="w-5 h-5" />
                </button>
              </div>

              {/* Columns */}
              <div className="space-y-2">
                {table.columns.map((column, columnIndex) => (
                  <div
                    key={columnIndex}
                    className="flex items-center space-x-2 p-2 bg-gray-50 rounded"
                  >
                    <input
                      type="text"
                      value={column.name}
                      onChange={(e) =>
                        updateColumn(tableIndex, columnIndex, { name: e.target.value })
                      }
                      className="flex-1 px-3 py-2 border border-gray-300 rounded text-sm"
                      placeholder="Column name"
                    />
                    <select
                      value={column.type}
                      onChange={(e) =>
                        updateColumn(tableIndex, columnIndex, { type: e.target.value })
                      }
                      className="w-32 px-3 py-2 border border-gray-300 rounded text-sm"
                    >
                      {columnTypes.map((type) => (
                        <option key={type} value={type}>
                          {type}
                        </option>
                      ))}
                    </select>
                    <button
                      onClick={() => removeColumn(tableIndex, columnIndex)}
                      className="p-2 text-red-600 hover:bg-red-100 rounded transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>

              {/* Add Column Button */}
              <button
                onClick={() => addColumn(tableIndex)}
                className="mt-3 flex items-center space-x-2 text-primary-600 hover:text-primary-700 text-sm font-medium"
              >
                <Plus className="w-4 h-4" />
                <span>Add Column</span>
              </button>
            </div>
          ))}

          {/* Add Table Button */}
          <button
            onClick={addTable}
            className="w-full py-4 border-2 border-dashed border-gray-300 rounded-lg text-gray-600 hover:border-primary-400 hover:text-primary-600 transition-colors flex items-center justify-center space-x-2"
          >
            <Plus className="w-5 h-5" />
            <span>Add Table</span>
          </button>
        </div>
      </div>
    </div>
  );
}

