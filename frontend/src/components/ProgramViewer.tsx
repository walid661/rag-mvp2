'use client'

import { useState, useEffect, useMemo } from 'react'
import ReactMarkdown from 'react-markdown'
import { CheckCircle2, Circle } from 'lucide-react'

interface ProgramViewerProps {
    content: string
}

interface ParsedSection {
    title: string
    content: string
    startIndex: number // To generate unique IDs for tasks
}

export default function ProgramViewer({ content }: ProgramViewerProps) {
    const [parsedSections, setParsedSections] = useState<ParsedSection[]>([])
    const [activeTab, setActiveTab] = useState(0)
    const [checkedState, setCheckedState] = useState<Record<string, boolean>>({})

    useEffect(() => {
        if (!content) return
        const sections = parseProgramText(content)
        setParsedSections(sections)
        setActiveTab(0)
        // Reset state on new content? Or persist? For now reset.
        setCheckedState({})
    }, [content])

    const parseProgramText = (text: string): ParsedSection[] => {
        const splitRegex = /((?:^|\n)(?:#{0,3}\s*)Day\s*\d+[^\n]*)/i
        const parts = text.split(splitRegex)

        const sections: ParsedSection[] = []
        let currentIndex = 0

        if (parts[0].trim()) {
            sections.push({
                title: "Overview",
                content: parts[0].trim(),
                startIndex: 0
            })
            currentIndex += parts[0].length
        }

        for (let i = 1; i < parts.length; i += 2) {
            const headerLine = parts[i]
            const body = parts[i + 1] || ""

            const dayMatch = headerLine.match(/Day\s*\d+/i)
            const title = dayMatch ? dayMatch[0] : "Day ?"
            const cleanHeader = headerLine.replace(/^\n/, '')

            sections.push({
                title: title,
                content: `${cleanHeader}${body}`.trim(),
                startIndex: currentIndex
            })

            currentIndex += headerLine.length + body.length
        }

        if (sections.length === 0 && text.trim()) {
            return [{ title: "Full Plan", content: text, startIndex: 0 }]
        }

        return sections
    }

    // Calculate Progress
    const { totalTasks, completedTasks, progressPercentage } = useMemo(() => {
        // Count total occurrences of "- [ ]" or "- [x]" in the raw content
        // Relaxed regex to handle variable spacing: - [ ] or -[ ]
        const taskRegex = /-\s*\[\s*[xX]?\s*\]/g
        const match = content.match(taskRegex)
        const total = match ? match.length : 0
        const completed = Object.values(checkedState).filter(Boolean).length
        const percentage = total > 0 ? Math.round((completed / total) * 100) : 0

        return { totalTasks: total, completedTasks: completed, progressPercentage: percentage }
    }, [content, checkedState])

    const toggleTask = (taskId: string) => {
        setCheckedState(prev => ({
            ...prev,
            [taskId]: !prev[taskId]
        }))
    }

    // Custom Renderer for the Active Tab
    const renderActiveContent = () => {
        if (!parsedSections[activeTab]) return null

        const section = parsedSections[activeTab]
        const lines = section.content.split('\n')

        let taskCounter = 0

        return (
            <div className="space-y-4">
                {lines.map((line, index) => {
                    // Check if line is a task
                    // Matches: "- [ ] Task", "- [x] Task", "-[ ] Task"
                    const taskMatch = line.match(/^-\s*\[\s*[xX]?\s*\]\s*(.*)/)

                    if (taskMatch) {
                        // Generate a unique ID for this task based on the section and its order
                        // We use a global-ish counter approach relative to the section
                        const taskId = `${section.title}-${taskCounter}`
                        taskCounter++
                        const isChecked = checkedState[taskId] || false
                        const taskText = taskMatch[1]

                        return (
                            <div
                                key={index}
                                onClick={() => toggleTask(taskId)}
                                className={`flex items-start gap-3 p-3 rounded-xl transition-all cursor-pointer border ${isChecked
                                        ? 'bg-green-900/20 border-green-900/50'
                                        : 'bg-zinc-900/50 border-zinc-800 hover:bg-zinc-800'
                                    }`}
                            >
                                <div className={`mt-1 transition-colors ${isChecked ? 'text-green-500' : 'text-gray-500'}`}>
                                    {isChecked ? <CheckCircle2 size={20} /> : <Circle size={20} />}
                                </div>
                                <div className={`flex-1 text-sm md:text-base ${isChecked ? 'line-through text-gray-500' : 'text-gray-200'}`}>
                                    <ReactMarkdown components={{ p: ({ children }) => <span>{children}</span> }}>
                                        {taskText}
                                    </ReactMarkdown>
                                </div>
                            </div>
                        )
                    }

                    // Simple heuristic: If it's a cue (starts with * Cue: or similar indentation), render it nicely
                    if (line.trim().startsWith('* Cue:') || line.trim().startsWith('*')) {
                        return (
                            <div key={index} className="pl-11 text-xs md:text-sm text-gray-400 -mt-2 mb-2">
                                <ReactMarkdown>{line}</ReactMarkdown>
                            </div>
                        )
                    }

                    // Regular text (headers, etc)
                    if (line.trim() === '') return <div key={index} className="h-2" />

                    return (
                        <div key={index} className="prose prose-invert prose-lg max-w-none">
                            <ReactMarkdown>{line}</ReactMarkdown>
                        </div>
                    )
                })}
            </div>
        )
    }

    if (!content) return null

    const showTabs = parsedSections.length > 1

    return (
        <div className="flex flex-col h-full relative">
            {/* Progress Bar (Sticky Top) */}
            {totalTasks > 0 && (
                <div className="sticky top-0 z-20 bg-black/95 border-b border-zinc-800 px-4 py-2">
                    <div className="flex justify-between text-xs text-gray-400 mb-1">
                        <span>Progress</span>
                        <span>{completedTasks}/{totalTasks} ({progressPercentage}%)</span>
                    </div>
                    <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
                        <div
                            className="h-full bg-blue-600 transition-all duration-500 ease-out"
                            style={{ width: `${progressPercentage}%` }}
                        />
                    </div>
                </div>
            )}

            {/* Tabs */}
            {showTabs && (
                <div className={`bg-zinc-900/50 border-b border-zinc-800 overflow-x-auto sticky ${totalTasks > 0 ? 'top-[45px]' : 'top-0'} z-10`}>
                    <div className="flex p-2 gap-2 min-w-max">
                        {parsedSections.map((section, index) => (
                            <button
                                key={index}
                                onClick={() => setActiveTab(index)}
                                className={`px-4 py-2 rounded-full text-sm font-bold transition-all whitespace-nowrap ${activeTab === index
                                        ? 'bg-white text-black shadow-lg scale-105'
                                        : 'bg-zinc-800 text-gray-400 hover:bg-zinc-700'
                                    }`}
                            >
                                {section.title}
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {/* Content */}
            <div className="flex-1 p-4 pb-32">
                {renderActiveContent()}
            </div>
        </div>
    )
}
