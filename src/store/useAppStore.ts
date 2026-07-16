import { create } from 'zustand';

export interface UserProfile {
  name: string;
  email: string;
  institution: string;
  department: string;
  loggedIn: boolean;
}

export interface UploadedFile {
  id: string;
  name: string;
  size: string;
  status: 'uploading' | 'completed' | 'failed';
  progress: number;
}

export interface BloomDistribution {
  remember: number;
  understand: number;
  apply: number;
  analyze: number;
  evaluate: number;
  create: number;
}

export interface GeneratedMCQ {
  id: string;
  question: string;
  options: string[];
  correctAnswer: string;
  bloomLevel: string;
  difficulty: 'easy' | 'medium' | 'hard';
  explanation: string;
  topic: string;
}

export interface GeneratedAssignment {
  id: string;
  question: string;
  marks: number;
  difficulty: 'easy' | 'medium' | 'hard';
  bloomLevel: string;
  questionType: 'short' | 'long' | 'analytical';
  rubric: string;
  answerKey: string;
  topic: string;
}

export interface GenerationHistoryItem {
  id: string;
  date: string;
  courseName: string;
  topic: string;
  mcqCount: number;
  assignmentCount: number;
  hasNotes: boolean;
  status: 'completed' | 'failed' | 'processing';
}

export interface AppState {
  // Theme & Navigation
  theme: 'light' | 'dark';
  sidebarOpen: boolean;
  activeTab: string;
  setTheme: (theme: 'light' | 'dark') => void;
  toggleSidebar: () => void;
  setActiveTab: (tab: string) => void;

  // Auth User
  user: UserProfile;
  setUser: (user: Partial<UserProfile>) => void;
  logout: () => void;

  // Configuration Selectors
  selectedDept: string;
  selectedSemester: string;
  selectedCourse: string;
  selectedUnit: string;
  selectedTopic: string;
  isConfigured: boolean;
  setConfig: (config: { dept: string; sem: string; course: string; unit: string; topic: string }) => void;
  resetConfig: () => void;

  // Resource Files
  uploadedFiles: UploadedFile[];
  addUploadedFile: (file: UploadedFile) => void;
  updateFileProgress: (id: string, progress: number, status?: UploadedFile['status']) => void;
  deleteFile: (id: string) => void;
  clearFiles: () => void;

  // Preferences
  teachingStyle: string;
  pedagogy: string;
  difficulty: 'easy' | 'medium' | 'hard';
  mcqCount: number;
  assignmentCount: number;
  bloomDistribution: BloomDistribution;
  setPreferences: (prefs: {
    teachingStyle?: string;
    pedagogy?: string;
    difficulty?: 'easy' | 'medium' | 'hard';
    mcqCount?: number;
    assignmentCount?: number;
    bloomDistribution?: Partial<BloomDistribution>;
  }) => void;

  // Generation Steps & Progress
  isGenerating: boolean;
  generationStep: number; // 0: Idle, 1: Planning, 2: Retrieving, 3: Generating, 4: Validating, 5: Deduplicating, 6: Formatted/Done
  generationStatusText: string;
  estimatedSecondsLeft: number;
  startGeneration: (onComplete?: () => void) => void;
  cancelGeneration: () => void;

  // Generated Outputs
  generatedNotes: {
    overview: string;
    conceptExplanation: string;
    workedExamples: string;
    activities: string;
    discussionQuestions: string;
    summary: string;
    revisionNotes: string;
  } | null;
  generatedMCQs: GeneratedMCQ[];
  generatedAssignments: GeneratedAssignment[];
  history: GenerationHistoryItem[];

  // Actions on Outputs
  updateMCQ: (id: string, updated: Partial<GeneratedMCQ>) => void;
  regenerateMCQ: (id: string) => void;
  deleteMCQ: (id: string) => void;
  updateAssignment: (id: string, updated: Partial<GeneratedAssignment>) => void;
  regenerateAssignment: (id: string) => void;
  deleteAssignment: (id: string) => void;
  updateNotesTab: (tab: string, content: string) => void;
  addToQuestionBank: (item: GeneratedMCQ | GeneratedAssignment) => void;
}

export const useAppStore = create<AppState>((set, get) => ({
  // Theme & UI Defaults
  theme: 'light',
  sidebarOpen: true,
  activeTab: 'dashboard',
  setTheme: (theme) => set({ theme }),
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setActiveTab: (activeTab) => set({ activeTab }),

  // User Profile
  user: {
    name: 'Dr. Prasanna Kumar',
    email: 'prasanna.k@academic.edu',
    institution: 'National Institute of Technology',
    department: 'Computer Science & Engineering',
    loggedIn: true, // Auto-logged in for mock experience
  },
  setUser: (updates) => set((state) => ({ user: { ...state.user, ...updates } })),
  logout: () => set((state) => ({ user: { ...state.user, loggedIn: false } })),

  // Config defaults
  selectedDept: '',
  selectedSemester: '',
  selectedCourse: '',
  selectedUnit: '',
  selectedTopic: '',
  isConfigured: false,
  setConfig: (config) =>
    set({
      selectedDept: config.dept,
      selectedSemester: config.sem,
      selectedCourse: config.course,
      selectedUnit: config.unit,
      selectedTopic: config.topic,
      isConfigured: true,
    }),
  resetConfig: () =>
    set({
      selectedDept: '',
      selectedSemester: '',
      selectedCourse: '',
      selectedUnit: '',
      selectedTopic: '',
      isConfigured: false,
    }),

  // Resource Upload
  uploadedFiles: [
    { id: 'f1', name: 'Textbook_Advanced_Algorithms_Ch3.pdf', size: '4.2 MB', status: 'completed', progress: 100 },
    { id: 'f2', name: 'Syllabus_CS402_Computer_Networks.pdf', size: '1.1 MB', status: 'completed', progress: 100 },
  ],
  addUploadedFile: (file) => set((state) => ({ uploadedFiles: [...state.uploadedFiles, file] })),
  updateFileProgress: (id, progress, status) =>
    set((state) => ({
      uploadedFiles: state.uploadedFiles.map((f) =>
        f.id === id ? { ...f, progress, ...(status ? { status } : {}) } : f
      ),
    })),
  deleteFile: (id) =>
    set((state) => ({
      uploadedFiles: state.uploadedFiles.filter((f) => f.id !== id),
    })),
  clearFiles: () => set({ uploadedFiles: [] }),

  // Preferences Defaults
  teachingStyle: 'socratic',
  pedagogy: 'bloom',
  difficulty: 'medium',
  mcqCount: 5,
  assignmentCount: 3,
  bloomDistribution: {
    remember: 20,
    understand: 30,
    apply: 20,
    analyze: 15,
    evaluate: 10,
    create: 5,
  },
  setPreferences: (prefs) =>
    set((state) => ({
      teachingStyle: prefs.teachingStyle ?? state.teachingStyle,
      pedagogy: prefs.pedagogy ?? state.pedagogy,
      difficulty: prefs.difficulty ?? state.difficulty,
      mcqCount: prefs.mcqCount ?? state.mcqCount,
      assignmentCount: prefs.assignmentCount ?? state.assignmentCount,
      bloomDistribution: prefs.bloomDistribution
        ? { ...state.bloomDistribution, ...prefs.bloomDistribution }
        : state.bloomDistribution,
    })),

  // Generator simulation variables
  isGenerating: false,
  generationStep: 0,
  generationStatusText: 'Idle',
  estimatedSecondsLeft: 0,
  startGeneration: (onComplete) => {
    set({ isGenerating: true, generationStep: 1, generationStatusText: 'Planner Agent: Generating lesson plan blueprint...', estimatedSecondsLeft: 12 });
    
    let timer: NodeJS.Timeout;
    let step = 1;
    const steps = [
      'Planner Agent: Generating lesson plan blueprint...',
      'Retrieval Agent: Fusing BM25 search with vector embeddings in Qdrant...',
      'Generator Agent: Streaming draft questions and concept notes...',
      'Validator Agent: Checking Bloom taxonomy alignment & syllabus compliance...',
      'Deduplication Agent: Verifying content originality against history database...',
      'Formatter Agent: Compiling output artifacts...',
    ];

    const runSimulation = () => {
      timer = setInterval(() => {
        step += 1;
        if (step <= 6) {
          set({
            generationStep: step,
            generationStatusText: steps[step - 1],
            estimatedSecondsLeft: Math.max(1, 14 - step * 2),
          });
        } else {
          clearInterval(timer);
          // Set generated mock content
          const topic = get().selectedTopic || 'Binary Search Trees & Balancing';
          
          set({
            isGenerating: false,
            generationStep: 6,
            estimatedSecondsLeft: 0,
            generationStatusText: 'Generation Complete!',
            generatedNotes: {
              overview: `This study module covers the core concepts of **${topic}**, focusing on their algorithmic structures, complexities, and real-world implications. Educators can utilize these formatted notes to guide lecture pacing and structure student reading assignments.`,
              conceptExplanation: `### Core Concept Explanation\n\n**${topic}** is a fundamental paradigm in data structures. By structuring nodes such that every left child is smaller than its parent, and every right child is larger, search operations can be carried out in logarithmic average time $O(\\log n)$.\n\n#### Key Characteristics:\n- **Search Complexity**: Average $O(\\log n)$, Worst-case $O(n)$ if the tree degenerates into a linear chain.\n- **Balancing Strategies**: AVL trees maintain a strict height balance factor of $\\le 1$, utilizing single/double rotations. Red-Black trees offer a slightly looser balance using color coding (red/black nodes) but require fewer restructuring rotations during modifications.\n- **Applications**: Database indexing (B-trees, B+ trees), syntax tree compilation, routers, and virtual memory mapping.`,
              workedExamples: `### Worked Example: Tree Rotations (AVL Tree)\n\nConsider an AVL tree undergoing insertion of nodes in ascending sequence: **[10, 20, 30]**.\n\n1. **Insert 10**: Root node. Balance factor = 0.\n2. **Insert 20**: Right child of 10. Balance factor of 10 becomes -1. Balance factor of 20 is 0.\n3. **Insert 30**: Right child of 20. Balance factor of 10 becomes -2 (UNBALANCED). Right-Right (RR) imbalance.\n\n#### Solution (Left Rotation on 10):\n- Node 20 becomes the new local root.\n- Node 10 becomes the left child of 20.\n- Node 30 remains the right child of 20.\n\n\`\`\`\n    10                     20\n      \\                   /  \\\n       20      ===>     10    30\n         \\\n          30\n\`\`\`\n*The search time is restored to optimized logarithmic levels.*`,
              activities: `### Classroom Activities & Hands-on Lab\n\n1. **Imbalance Drawing Bee** (15 mins):\n   Divide class into pairs. Partner A designs an unbalanced binary tree insertion scenario (up to 6 elements), and Partner B must identify the imbalance type (LL, LR, RR, RL) and draw the resulting rotations. Swap roles.\n\n2. **Code Implementation Challenge**:\n   Write a quick recursive function in Python to verify if a given Binary Tree satisfies the Binary Search Tree property. Highlight why simple localized checks (only checking immediate parent-child nodes) are insufficient.`,
              discussionQuestions: `### Discussion Questions for Seminars\n\n- *Why do commercial databases (like PostgreSQL/MySQL) choose B/B+ trees instead of traditional AVL trees or Red-Black trees for index storage?*\n- *Is it computationally viable to rebalance a self-balancing binary search tree on every single node modification in real-time, high-frequency systems? What are the trade-offs?*`,
              summary: `### Summary Sheet\n\n- Binary Search Trees (BSTs) optimize search, insertion, and deletion speeds to $O(\\log n)$ in balanced configurations.\n- Degeneration to $O(n)$ occurs without deliberate balancing policies.\n- AVL trees emphasize retrieval efficiency (strict balance), while Red-Black trees balance write vs. retrieval efficiency (more lenient balance rules, fewer rotations).`,
              revisionNotes: `### Core Revision Checklist\n\n- [ ] State the BST property.\n- [ ] Compare AVL and Red-Black tree insertion complexities.\n- [ ] Sketch single (LL/RR) and double (LR/RL) AVL rotation states.\n- [ ] Compute tree height and balance factors for a sample 8-node tree.`,
            },
            generatedMCQs: [
              {
                id: 'm1',
                question: 'Which of the following self-balancing binary search trees maintains a strict height balance factor where the difference in height between left and right subtrees is at most 1?',
                options: ['AVL Tree', 'Red-Black Tree', 'Splay Tree', 'B-Tree'],
                correctAnswer: 'AVL Tree',
                bloomLevel: 'Remember',
                difficulty: 'easy',
                explanation: 'An AVL tree is defined by its strict balance factor, where for every node, the height difference between left and right subtrees cannot exceed 1. Red-Black trees are less strictly balanced.',
                topic: topic,
              },
              {
                id: 'm2',
                question: 'Consider an AVL tree containing elements [15, 10, 8]. What rotation type is required to restore AVL balance balance upon inserting the element 8?',
                options: ['Left Rotation (LL)', 'Right Rotation (LL)', 'Left-Right Rotation (LR)', 'Right-Left Rotation (RL)'],
                correctAnswer: 'Right Rotation (LL)',
                bloomLevel: 'Apply',
                difficulty: 'medium',
                explanation: 'Inserting 10 and then 8 into 15 creates a left-left line (LL imbalance). A single Right rotation centered on 15 resolves the imbalance, making 10 the new root.',
                topic: topic,
              },
              {
                id: 'm3',
                question: 'Under what condition does search complexity in a standard, un-balanced Binary Search Tree degenerate to O(n)?',
                options: [
                  'When elements are inserted in random uniform order',
                  'When elements are inserted in sorted order',
                  'When the tree contains a balance factor of exactly 0 at all times',
                  'When the tree height matches log2(n)',
                ],
                correctAnswer: 'When elements are inserted in sorted order',
                bloomLevel: 'Analyze',
                difficulty: 'medium',
                explanation: 'If elements are inserted in sorted order, the BST grows linearly (skewed tree), representing a linked list structure and degenerating search complexity to O(n).',
                topic: topic,
              },
              {
                id: 'm4',
                question: 'Compare AVL trees and Red-Black trees. Under which scenario would a Red-Black tree be preferred over an AVL tree?',
                options: [
                  'In read-intensive workloads with minimal insertions',
                  'In write-intensive workloads with frequent insertions and deletions',
                  'When strict logarithmic search times must be guaranteed',
                  'When disk-space memory is heavily constrained',
                ],
                correctAnswer: 'In write-intensive workloads with frequent insertions and deletions',
                bloomLevel: 'Evaluate',
                difficulty: 'hard',
                explanation: 'Red-Black trees require fewer rotations during insertions/deletions than AVL trees because of their looser balance conditions. Therefore, they excel in write-heavy settings.',
                topic: topic,
              },
              {
                id: 'm5',
                question: 'Analyze why B+ Trees are preferred over Red-Black Trees for implementation in database file systems storage.',
                options: [
                  'B+ Trees have higher heights, increasing disk search paths',
                  'B+ Trees store all actual data in leaf nodes and have large branching factors, minimizing disk I/O operations',
                  'Red-Black Trees require O(n log n) search times on disk',
                  'B+ Trees are simpler to implement and rotate in memory',
                ],
                correctAnswer: 'B+ Trees store all actual data in leaf nodes and have large branching factors, minimizing disk I/O operations',
                bloomLevel: 'Create',
                difficulty: 'hard',
                explanation: 'Due to flat heights and massive branching factors (fan-out), B+ Trees match disk block structures and minimize latency of disk head movements.',
                topic: topic,
              },
            ],
            generatedAssignments: [
              {
                id: 'a1',
                question: 'Design a self-balancing AVL tree by inserting the following sequence: [35, 18, 45, 12, 28, 38, 50, 20, 30]. Show the step-by-step state of the tree, identify any imbalances, and specify the rotations performed to maintain AVL balancing properties.',
                marks: 15,
                difficulty: 'medium',
                bloomLevel: 'Apply',
                questionType: 'analytical',
                rubric: '5 marks: Correct placement of initial elements. 5 marks: Correctly identifying LL/RR/LR imbalance states. 5 marks: Correct representation of tree rotations and final balanced height.',
                answerKey: 'Imbalance occurs after inserting 20 (causing LR imbalance at root element 35). A double rotation (Left-Right) centered on 18/28 restores AVL height.',
                topic: topic,
              },
              {
                id: 'a2',
                question: 'Analyze the worst-case space and time complexities of executing an in-order traversal on a Red-Black tree vs. an unbalanced Binary Search Tree of n elements. Explain how the height guarantees of Red-Black Trees prevent recursion stack overflow issues in memory.',
                marks: 10,
                difficulty: 'hard',
                bloomLevel: 'Analyze',
                questionType: 'short',
                rubric: '3 marks: Correct time complexity (O(n) for both). 3 marks: Correct recursion depth argument (O(log n) for Red-Black, O(n) for BST). 4 marks: Logical analysis of memory overflow prevention.',
                answerKey: 'Both operations require O(n) time. However, the stack depth for AVL/RB trees is limited to O(log n), whereas an unbalanced BST can require O(n) stack frames, raising stack overflow risks.',
                topic: topic,
              },
              {
                id: 'a3',
                question: 'Propose a pedagogical coding task where students construct a customized splay tree. Detail the rubric criteria to evaluate students understanding of amortized O(log n) performance vs. strict worst-case limits.',
                marks: 20,
                difficulty: 'hard',
                bloomLevel: 'Create',
                questionType: 'long',
                rubric: '5 marks: Splaying operation implementation. 5 marks: Amortized complexity analysis. 5 marks: Rubric completeness. 5 marks: Coding style guide.',
                answerKey: 'Students should implement standard zig-zig, zig-zag splays. The rubric should measure code correctness, comparative runtime measurements against standard BSTs, and written amortized complexity writeups.',
                topic: topic,
              },
            ],
            history: [
              {
                id: 'h_' + Date.now(),
                date: new Date().toLocaleDateString(),
                courseName: get().selectedCourse || 'Data Structures (CS-301)',
                topic: topic,
                mcqCount: get().mcqCount,
                assignmentCount: get().assignmentCount,
                hasNotes: true,
                status: 'completed',
              },
              ...get().history,
            ],
          });
          
          if (onComplete) onComplete();
        }
      }, 1500);
    };

    runSimulation();
  },
  cancelGeneration: () => {
    set({ isGenerating: false, generationStep: 0, generationStatusText: 'Generation cancelled' });
  },

  // Generated lists
  generatedNotes: null,
  generatedMCQs: [],
  generatedAssignments: [],
  history: [
    {
      id: 'h_1',
      date: '2026-07-10',
      courseName: 'Data Structures (CS-301)',
      topic: 'AVL Trees & Balancing Rotations',
      mcqCount: 5,
      assignmentCount: 2,
      hasNotes: true,
      status: 'completed',
    },
    {
      id: 'h_2',
      date: '2026-07-08',
      courseName: 'Software Engineering (CS-402)',
      topic: 'Design Patterns: Singleton & Factory',
      mcqCount: 10,
      assignmentCount: 4,
      hasNotes: true,
      status: 'completed',
    },
    {
      id: 'h_3',
      date: '2026-07-02',
      courseName: 'Database Management Systems (CS-302)',
      topic: 'ACID Transactions & Lock Schedules',
      mcqCount: 8,
      assignmentCount: 3,
      hasNotes: false,
      status: 'completed',
    },
  ],

  // Actions
  updateMCQ: (id, updated) =>
    set((state) => ({
      generatedMCQs: state.generatedMCQs.map((m) => (m.id === id ? { ...m, ...updated } : m)),
    })),
  regenerateMCQ: (id) =>
    set((state) => ({
      generatedMCQs: state.generatedMCQs.map((m) =>
        m.id === id
          ? {
              ...m,
              question: m.question + ' (Regenerated for quality alignment)',
              options: [m.options[1], m.options[0], m.options[2], m.options[3]],
            }
          : m
      ),
    })),
  deleteMCQ: (id) =>
    set((state) => ({
      generatedMCQs: state.generatedMCQs.filter((m) => m.id !== id),
    })),

  updateAssignment: (id, updated) =>
    set((state) => ({
      generatedAssignments: state.generatedAssignments.map((a) => (a.id === id ? { ...a, ...updated } : a)),
    })),
  regenerateAssignment: (id) =>
    set((state) => ({
      generatedAssignments: state.generatedAssignments.map((a) =>
        a.id === id
          ? {
              ...a,
              question: a.question + ' (Revised for pedagogical clarity)',
              rubric: a.rubric + '\n- 5 marks added for code elegance verification.',
            }
          : a
      ),
    })),
  deleteAssignment: (id) =>
    set((state) => ({
      generatedAssignments: state.generatedAssignments.filter((a) => a.id !== id),
    })),

  updateNotesTab: (tab, content) =>
    set((state) => {
      if (!state.generatedNotes) return {};
      return {
        generatedNotes: {
          ...state.generatedNotes,
          [tab]: content,
        },
      };
    }),

  addToQuestionBank: (item) => {
    // Add to history database simulation
  },
}));
