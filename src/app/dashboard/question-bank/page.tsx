'use client';

import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Database,
  Search,
  Filter,
  Download,
  Trash2,
  Star,
  CheckSquare,
  Square,
  ChevronRight,
  Bookmark,
  Sparkles,
  ChevronLeft,
} from 'lucide-react';

interface BankItem {
  id: string;
  question: string;
  type: 'MCQ' | 'Assignment';
  bloomLevel: string;
  difficulty: 'easy' | 'medium' | 'hard';
  topic: string;
  marks?: number;
  explanation?: string;
  rubric?: string;
  answerKey: string;
  favorite?: boolean;
}

export default function QuestionBankPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [difficultyFilter, setDifficultyFilter] = useState('all');
  const [selectedItems, setSelectedItems] = useState<string[]>([]);
  const [selectedQuestion, setSelectedQuestion] = useState<BankItem | null>(null);
  const [page, setPage] = useState(1);

  // Mock Question Bank List
  const [bank, setBank] = useState<BankItem[]>([
    {
      id: 'qb_1',
      question: 'Which tree traversal visits the nodes in ascending sorted order in a Binary Search Tree?',
      type: 'MCQ',
      bloomLevel: 'Remember',
      difficulty: 'easy',
      topic: 'Binary Search Trees',
      answerKey: 'In-order Traversal',
      explanation: 'An in-order traversal of a BST visits the left child, the parent, and then the right child, which naturally prints the keys in sorted order.',
      favorite: true,
    },
    {
      id: 'qb_2',
      question: 'Design a self-balancing AVL tree by inserting the following sequence: [30, 20, 10, 8, 40]. Highlight each rotation.',
      type: 'Assignment',
      bloomLevel: 'Apply',
      difficulty: 'medium',
      topic: 'AVL Trees',
      marks: 15,
      rubric: '5 marks: Elements placed. 5 marks: Imbalances found. 5 marks: Correct balanced shape drawing.',
      answerKey: 'LL rotation occurs at 30 when 10 is inserted, making 20 the root. RL rotation occurs at root when 8 is added.',
      favorite: false,
    },
    {
      id: 'qb_3',
      question: 'Compare the search complexities of AVL trees and Splay trees. Detail the difference between strict height balance and amortized limits.',
      type: 'Assignment',
      bloomLevel: 'Analyze',
      difficulty: 'hard',
      topic: 'Advanced Trees',
      marks: 10,
      rubric: '4 marks: AVL logarithmic guarantees. 4 marks: Splay amortized properties. 2 marks: Code comparison.',
      answerKey: 'AVL maintains strict balance height <= log n on every step. Splay tree offers amortized O(log n) but worst-case O(n) for a single operation.',
      favorite: true,
    },
    {
      id: 'qb_4',
      question: 'In a Red-Black Tree, what is the maximum possible height of a tree with n nodes?',
      type: 'MCQ',
      bloomLevel: 'Understand',
      difficulty: 'medium',
      topic: 'Red-Black Trees',
      answerKey: '2 * log2(n + 1)',
      explanation: 'A Red-Black Tree height is guaranteed to be at most 2 * log2(n + 1) because the longest path (alternating red/black) cannot be more than twice the length of the shortest path (all black).',
      favorite: false,
    },
    {
      id: 'qb_5',
      question: 'Evaluate the use case of B-Trees in operating system disk indexing over standard Binary Search Trees.',
      type: 'Assignment',
      bloomLevel: 'Evaluate',
      difficulty: 'hard',
      topic: 'B-Trees',
      marks: 20,
      rubric: '10 marks: Block access arguments. 5 marks: Height limits. 5 marks: Cache footprint benefits.',
      answerKey: 'B-Trees fit hardware block dimensions, reducing search height to 3-4 blocks and limiting slow physical disk head seeks.',
      favorite: false,
    },
  ]);

  // Handle Search & Filtering
  const filteredBank = bank.filter((item) => {
    const matchesSearch = item.question.toLowerCase().includes(searchTerm.toLowerCase()) || item.topic.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesType = typeFilter === 'all' || item.type === typeFilter;
    const matchesDifficulty = difficultyFilter === 'all' || item.difficulty === difficultyFilter;
    return matchesSearch && matchesType && matchesDifficulty;
  });

  const toggleFavorite = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setBank((prev) =>
      prev.map((item) => (item.id === id ? { ...item, favorite: !item.favorite } : item))
    );
    if (selectedQuestion?.id === id) {
      setSelectedQuestion((prev) => (prev ? { ...prev, favorite: !prev.favorite } : null));
    }
  };

  const toggleSelection = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedItems((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const toggleSelectAll = () => {
    if (selectedItems.length === filteredBank.length) {
      setSelectedItems([]);
    } else {
      setSelectedItems(filteredBank.map((item) => item.id));
    }
  };

  const handleBulkExport = () => {
    const selectedData = bank.filter((item) => selectedItems.includes(item.id));
    const dataStr = JSON.stringify(selectedData, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Selected_Questions_${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="font-heading font-bold text-2xl tracking-tight">Curricular Question Bank</h2>
          <p className="text-xs text-muted-custom">Search, audit, and compile historical generated questions.</p>
        </div>

        {selectedItems.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-primary">{selectedItems.length} selected</span>
            <Button size="sm" variant="outline" className="text-xs" onClick={handleBulkExport}>
              <Download className="h-4 w-4 mr-1.5" /> Export Selected
            </Button>
          </div>
        )}
      </div>

      {/* Filters Toolbar */}
      <div className="flex flex-col md:flex-row gap-4 items-center justify-between p-4 bg-card border border-border-custom rounded-2xl">
        <div className="flex items-center gap-2 w-full md:w-auto">
          <Search className="h-4 w-4 text-muted-custom shrink-0" />
          <input
            type="text"
            placeholder="Search by keyword or topic..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full md:w-60 bg-transparent border-0 text-xs focus:ring-0 focus:outline-hidden text-foreground placeholder:text-muted-custom/60"
          />
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto justify-end">
          {/* Select Type */}
          <div className="flex items-center gap-1.5 text-xs">
            <Filter className="h-3.5 w-3.5 text-muted-custom" />
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="py-1 px-2 text-[11px] rounded-lg border border-border-custom bg-bg-secondary"
            >
              <option value="all">All Types</option>
              <option value="MCQ">MCQ Quizzes</option>
              <option value="Assignment">Assignments</option>
            </select>
          </div>

          {/* Select Difficulty */}
          <div className="flex items-center gap-1.5 text-xs">
            <Filter className="h-3.5 w-3.5 text-muted-custom" />
            <select
              value={difficultyFilter}
              onChange={(e) => setDifficultyFilter(e.target.value)}
              className="py-1 px-2 text-[11px] rounded-lg border border-border-custom bg-bg-secondary"
            >
              <option value="all">All Difficulties</option>
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
            </select>
          </div>
        </div>
      </div>

      {/* Split Layout Pane */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
        
        {/* Left Side: Question List (3/5 columns) */}
        <div className="lg:col-span-3 space-y-4">
          <div className="flex items-center justify-between px-2 text-xs">
            <button
              onClick={toggleSelectAll}
              className="flex items-center gap-2 font-semibold text-muted-custom hover:text-foreground cursor-pointer"
            >
              {selectedItems.length === filteredBank.length ? (
                <CheckSquare className="h-4 w-4 text-primary" />
              ) : (
                <Square className="h-4 w-4" />
              )}
              Select All ({filteredBank.length} questions)
            </button>
            <span className="text-muted-custom font-semibold">Showing 1-{filteredBank.length}</span>
          </div>

          <div className="space-y-3">
            {filteredBank.map((item) => (
              <div
                key={item.id}
                onClick={() => setSelectedQuestion(item)}
                className={`p-4 rounded-2xl border text-xs flex gap-4 transition-all cursor-pointer ${
                  selectedQuestion?.id === item.id
                    ? 'bg-primary/5 border-primary shadow-xs'
                    : 'bg-card border-border-custom hover:border-border-custom hover:shadow-xs'
                }`}
              >
                {/* Checkbox selector */}
                <button
                  onClick={(e) => toggleSelection(item.id, e)}
                  className="mt-0.5 text-muted-custom hover:text-foreground shrink-0 cursor-pointer"
                >
                  {selectedItems.includes(item.id) ? (
                    <CheckSquare className="h-4 w-4 text-primary" />
                  ) : (
                    <Square className="h-4 w-4" />
                  )}
                </button>

                {/* Question Info */}
                <div className="flex-1 space-y-2 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-muted-custom uppercase text-[9px]">{item.type}</span>
                    <span className="text-muted-custom/60">&bull;</span>
                    <span className="text-[10px] text-muted-custom font-medium truncate">{item.topic}</span>
                  </div>
                  <p className="font-bold text-sm leading-normal truncate">{item.question}</p>
                  
                  {/* Badges */}
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded-md bg-primary/10 text-primary font-bold text-[9px]">
                      {item.bloomLevel}
                    </span>
                    <span className={`px-2 py-0.5 rounded-md font-semibold text-[9px] ${
                      item.difficulty === 'easy'
                        ? 'bg-green-500/10 text-green-600'
                        : item.difficulty === 'medium'
                        ? 'bg-amber-500/10 text-amber-600'
                        : 'bg-red-500/10 text-red-600'
                    }`}>
                      {item.difficulty}
                    </span>
                  </div>
                </div>

                {/* Right actions (Favorite toggle) */}
                <div className="flex flex-col justify-between items-end shrink-0">
                  <button
                    onClick={(e) => toggleFavorite(item.id, e)}
                    className={`h-8 w-8 rounded-lg flex items-center justify-center cursor-pointer transition-colors ${
                      item.favorite ? 'text-amber-500 hover:text-amber-600' : 'text-muted-custom hover:text-foreground'
                    }`}
                  >
                    <Star className={`h-4.5 w-4.5 ${item.favorite ? 'fill-current' : ''}`} />
                  </button>
                  <ChevronRight className="h-4.5 w-4.5 text-muted-custom" />
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-center gap-4 pt-4 text-xs font-semibold text-muted-custom">
            <button className="h-8 px-3 rounded-lg border border-border-custom flex items-center gap-1 hover:bg-muted-bg disabled:opacity-40" disabled>
              <ChevronLeft className="h-4 w-4" /> Previous
            </button>
            <span>Page {page} of 1</span>
            <button className="h-8 px-3 rounded-lg border border-border-custom flex items-center gap-1 hover:bg-muted-bg disabled:opacity-40" disabled>
              Next <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Right Side: Detailed Preview panel (2/5 columns) */}
        <div className="lg:col-span-2">
          {selectedQuestion ? (
            <Card className="border border-border-custom bg-card sticky top-20">
              <CardHeader className="flex flex-row items-center justify-between pb-4 border-b border-border-custom/40 bg-bg-secondary/15">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-semibold text-muted-custom uppercase text-[9px]">{selectedQuestion.type}</span>
                    {selectedQuestion.marks && (
                      <span className="px-1.5 py-0.5 rounded-md bg-amber-500/10 text-amber-600 dark:text-amber-500 font-bold text-[9px]">
                        {selectedQuestion.marks} Marks
                      </span>
                    )}
                  </div>
                  <CardTitle className="text-sm font-bold">Metadata Profile</CardTitle>
                </div>
                <button
                  onClick={(e) => toggleFavorite(selectedQuestion.id, e)}
                  className={`h-8 w-8 rounded-lg flex items-center justify-center cursor-pointer ${
                    selectedQuestion.favorite ? 'text-amber-500' : 'text-muted-custom'
                  }`}
                >
                  <Star className={`h-4.5 w-4.5 ${selectedQuestion.favorite ? 'fill-current' : ''}`} />
                </button>
              </CardHeader>
              <CardContent className="p-6 space-y-4 text-xs leading-relaxed">
                
                {/* Question */}
                <div className="space-y-1">
                  <h4 className="font-semibold text-muted-custom">Question Context</h4>
                  <p className="font-bold text-sm text-foreground leading-normal">{selectedQuestion.question}</p>
                </div>

                {/* Topic and Tags */}
                <div className="grid grid-cols-2 gap-4 py-2 border-t border-b border-border-custom/40">
                  <div>
                    <h5 className="font-semibold text-muted-custom">Syllabus Topic</h5>
                    <p className="font-bold">{selectedQuestion.topic}</p>
                  </div>
                  <div>
                    <h5 className="font-semibold text-muted-custom">Bloom Level</h5>
                    <p className="font-bold text-primary">{selectedQuestion.bloomLevel}</p>
                  </div>
                </div>

                {/* Answer key / Explanation / Rubrics */}
                <div className="space-y-2">
                  <h4 className="font-semibold text-muted-custom">Correct Answer Target</h4>
                  <div className="p-3 bg-bg-secondary rounded-xl font-mono leading-normal border border-border-custom/40">
                    {selectedQuestion.answerKey}
                  </div>
                </div>

                {selectedQuestion.explanation && (
                  <div className="space-y-1">
                    <h4 className="font-semibold text-muted-custom">Factual Grounded Explanation</h4>
                    <p className="text-muted-custom leading-normal">{selectedQuestion.explanation}</p>
                  </div>
                )}

                {selectedQuestion.rubric && (
                  <div className="space-y-1">
                    <h4 className="font-semibold text-muted-custom">Grading Rubric Criteria</h4>
                    <p className="text-muted-custom leading-normal font-sans bg-bg-secondary p-3.5 rounded-xl border border-border-custom/40">
                      {selectedQuestion.rubric}
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          ) : (
            <Card className="border border-border-custom bg-card text-center p-8 sticky top-20 text-muted-custom h-72 flex flex-col justify-center">
              <Database className="h-8 w-8 mx-auto mb-3" />
              <p className="text-xs font-semibold">Select a question to review its answer keys, grading rubrics, and source citations.</p>
            </Card>
          )}
        </div>

      </div>
    </div>
  );
}
