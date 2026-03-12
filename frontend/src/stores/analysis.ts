import { defineStore } from 'pinia'
import type { AnalysisState, TaskNode, AnalysisResult } from '@/types'

interface StoreState {
  analysisState: AnalysisState
  result: AnalysisResult | null
  searchHistory: string[]
  sidebarOpen: boolean
}

export const useAnalysisStore = defineStore('analysis', {
  state: (): StoreState => ({
    analysisState: {
      session_id: '',
      status: 'idle',
      progress: 0,
      current_step: '',
      tasks: [],
      errors: [],
    },
    result: null,
    searchHistory: [],
    sidebarOpen: false,
  }),

  getters: {
    isAnalyzing: (state) => state.analysisState.status === 'running',
    hasErrors: (state) => (state.analysisState.errors?.length || 0) > 0,
    completedTasks: (state) => 
      state.analysisState.tasks.filter(t => t.status === 'completed'),
    runningTasks: (state) => 
      state.analysisState.tasks.filter(t => t.status === 'running'),
  },

  actions: {
    setAnalysisState(state: Partial<AnalysisState>) {
      this.analysisState = { ...this.analysisState, ...state }
    },

    setResult(result: AnalysisResult | null) {
      this.result = result
    },

    addToHistory(query: string) {
      if (!this.searchHistory.includes(query)) {
        this.searchHistory.unshift(query)
        if (this.searchHistory.length > 10) {
          this.searchHistory = this.searchHistory.slice(0, 10)
        }
      }
    },

    clearHistory() {
      this.searchHistory = []
    },

    addTask(task: TaskNode) {
      this.analysisState.tasks.push(task)
    },

    updateTask(taskId: string, updates: Partial<TaskNode>) {
      const index = this.analysisState.tasks.findIndex(t => t.id === taskId)
      if (index !== -1) {
        this.analysisState.tasks[index] = {
          ...this.analysisState.tasks[index],
          ...updates,
        }
      }
    },

    updateProgress(progress: number) {
      this.analysisState.progress = Math.min(100, Math.max(0, progress))
    },

    reset() {
      this.analysisState = {
        session_id: '',
        status: 'idle',
        progress: 0,
        current_step: '',
        tasks: [],
        errors: [],
      }
      this.result = null
    },

    toggleSidebar() {
      this.sidebarOpen = !this.sidebarOpen
    },
  },
})
