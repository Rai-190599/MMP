import { useEffect, useState } from 'react'
import { tasksApi } from '../../api/client.js'
import LoadingSpinner from '../../components/LoadingSpinner.jsx'
import { useOrganizerEvents } from '../../hooks/useOrganizerEvents.js'
import styles from './TaskBoard.module.css'

const COLUMNS = [
  { key: 'todo', label: 'To Do', color: '#dbeafe' },
  { key: 'in_progress', label: 'In Progress', color: '#fef3c7' },
  { key: 'done', label: 'Done', color: '#d1fae5' },
]

const NEXT_STATUS = { todo: 'in_progress', in_progress: 'done', done: 'todo' }

const CATEGORIES = ['sponsors', 'tshirt', 'bib', 'volunteers', 'logistics']

const EMPTY_FORM = { title: '', category: 'logistics', assignee_id: '', deadline: '' }

export default function TaskBoard() {
  const { events, selectedId, setSelectedId } = useOrganizerEvents()
  const [columns, setColumns] = useState({ todo: [], in_progress: [], done: [] })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [categoryFilter, setCategoryFilter] = useState('')

  // Add-task form state: { columnKey | null }
  const [addingIn, setAddingIn] = useState(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [formLoading, setFormLoading] = useState(false)
  const [formError, setFormError] = useState(null)

  useEffect(() => {
    if (selectedId) loadTasks()
  }, [categoryFilter, selectedId])

  async function loadTasks() {
    if (!selectedId) return
    setLoading(true)
    setError(null)
    try {
      const params = { event_id: selectedId }
      if (categoryFilter) params.category = categoryFilter
      const data = await tasksApi.list(params)
      setColumns(data)
    } catch {
      setError('Failed to load tasks.')
    } finally {
      setLoading(false)
    }
  }

  async function cycleStatus(task) {
    const next = NEXT_STATUS[task.status]
    try {
      const updated = await tasksApi.update(task.id, { status: next })
      setColumns((prev) => {
        // Remove from old column, add to new
        const oldCol = prev[task.status].filter((t) => t.id !== task.id)
        const newCol = [...prev[next], updated]
        return { ...prev, [task.status]: oldCol, [next]: newCol }
      })
    } catch {
      // silent — UI stays unchanged
    }
  }

  async function deleteTask(task) {
    try {
      await tasksApi.remove(task.id)
      setColumns((prev) => ({
        ...prev,
        [task.status]: prev[task.status].filter((t) => t.id !== task.id),
      }))
    } catch {
      // silent
    }
  }

  async function toggleChecklist(task, index, done) {
    // Optimistic update
    const optimistic = {
      ...task,
      checklist: task.checklist.map((item, i) => (i === index ? { ...item, done } : item)),
    }
    setColumns((prev) => ({
      ...prev,
      [task.status]: prev[task.status].map((t) => (t.id === task.id ? optimistic : t)),
    }))
    try {
      const updated = await tasksApi.updateChecklist(task.id, index, done)
      setColumns((prev) => ({
        ...prev,
        [task.status]: prev[task.status].map((t) => (t.id === task.id ? updated : t)),
      }))
    } catch {
      // Revert optimistic update on failure
      setColumns((prev) => ({
        ...prev,
        [task.status]: prev[task.status].map((t) => (t.id === task.id ? task : t)),
      }))
    }
  }

  function openAddForm(colKey) {
    setAddingIn(colKey)
    setForm(EMPTY_FORM)
    setFormError(null)
  }

  function closeAddForm() {
    setAddingIn(null)
    setFormError(null)
  }

  async function submitAddTask(colKey) {
    if (!form.title.trim()) {
      setFormError('Title is required')
      return
    }
    setFormLoading(true)
    setFormError(null)
    try {
      const payload = {
        event_id: selectedId,
        title: form.title.trim(),
        category: form.category,
        assignee_id: form.assignee_id || undefined,
        deadline: form.deadline || undefined,
        checklist: [],
      }
      const created = await tasksApi.create(payload)
      setColumns((prev) => ({
        ...prev,
        todo: [...prev.todo, created],  // new tasks always start in todo
      }))
      closeAddForm()
    } catch (err) {
      setFormError(err?.response?.data?.detail || 'Failed to create task')
    } finally {
      setFormLoading(false)
    }
  }

  if (loading) return <LoadingSpinner text="Loading task board…" />
  if (error) return <div className="page-container"><p className="error-msg">{error}</p></div>

  return (
    <div className="page-container">
      <div className={styles.header}>
        <h1 className={styles.heading}>Task Board</h1>
        <div className={styles.filters}>
          {events.length > 1 && (
            <select
              value={selectedId}
              onChange={(e) => { setSelectedId(e.target.value); setCategoryFilter('') }}
              style={{ marginRight: '0.75rem' }}
            >
              {events.map((ev) => (
                <option key={ev.id} value={ev.id}>{ev.name}</option>
              ))}
            </select>
          )}
          <label htmlFor="cat-filter" className={styles.filterLabel}>Category:</label>
          <select
            id="cat-filter"
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className={styles.filterSelect}
          >
            <option value="">All</option>
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
      </div>

      <div className={styles.board}>
        {COLUMNS.map((col) => (
          <div key={col.key} className={styles.column}>
            <div className={styles.colHeader} style={{ background: col.color }}>
              <span className={styles.colTitle}>{col.label}</span>
              <span className={styles.colCount}>{columns[col.key].length}</span>
            </div>

            <div className={styles.cardList}>
              {columns[col.key].map((task) => (
                <TaskCard
                  key={task.id}
                  task={task}
                  onCycleStatus={cycleStatus}
                  onDelete={deleteTask}
                  onToggleChecklist={toggleChecklist}
                />
              ))}

              {/* Add task form / button */}
              {addingIn === col.key ? (
                <div className={styles.addForm}>
                  <input
                    type="text"
                    placeholder="Task title"
                    value={form.title}
                    onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
                    className={styles.addInput}
                    autoFocus
                  />
                  <select
                    value={form.category}
                    onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))}
                    className={styles.addSelect}
                  >
                    {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
                  </select>
                  <input
                    type="date"
                    value={form.deadline}
                    onChange={(e) => setForm((f) => ({ ...f, deadline: e.target.value }))}
                    className={styles.addInput}
                  />
                  {formError && <p className="error-msg" style={{ fontSize: '0.8rem' }}>{formError}</p>}
                  <div className={styles.addActions}>
                    <button
                      className="btn-primary btn-sm"
                      onClick={() => submitAddTask(col.key)}
                      disabled={formLoading}
                    >
                      {formLoading ? '…' : 'Add'}
                    </button>
                    <button className="btn-secondary btn-sm" onClick={closeAddForm}>Cancel</button>
                  </div>
                </div>
              ) : (
                <button
                  className={styles.addBtn}
                  onClick={() => openAddForm(col.key)}
                  data-testid={`add-task-${col.key}`}
                >
                  + Add task
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function TaskCard({ task, onCycleStatus, onDelete, onToggleChecklist }) {
  const doneCount = task.checklist.filter((i) => i.done).length
  const totalCount = task.checklist.length

  return (
    <div className={styles.card} data-testid={`task-card-${task.id}`}>
      <div className={styles.cardTop}>
        <span className={`${styles.categoryBadge} ${styles[`cat_${task.category}`]}`}>
          {task.category}
        </span>
        <button
          className={styles.deleteBtn}
          onClick={() => onDelete(task)}
          title="Delete task"
          data-testid={`delete-task-${task.id}`}
        >
          ×
        </button>
      </div>

      <p className={styles.cardTitle}>{task.title}</p>

      {task.assignee && (
        <p className={styles.assignee}>👤 {task.assignee.name}</p>
      )}

      {task.deadline && (
        <p className={styles.deadline}>📅 {task.deadline}</p>
      )}

      {totalCount > 0 && (
        <div className={styles.checklist}>
          <p className={styles.checklistProgress}>{doneCount}/{totalCount} done</p>
          {task.checklist.map((item, idx) => (
            <label key={idx} className={styles.checkItem}>
              <input
                type="checkbox"
                checked={item.done}
                onChange={(e) => onToggleChecklist(task, idx, e.target.checked)}
              />
              <span style={{ textDecoration: item.done ? 'line-through' : 'none', color: item.done ? '#9ca3af' : 'inherit' }}>
                {item.item}
              </span>
            </label>
          ))}
        </div>
      )}

      <div className={styles.cardFooter}>
        <button
          className={styles.statusBadge}
          onClick={() => onCycleStatus(task)}
          title="Click to advance status"
          data-testid={`status-badge-${task.id}`}
        >
          {task.status.replace(/_/g, ' ')} →
        </button>
      </div>
    </div>
  )
}
