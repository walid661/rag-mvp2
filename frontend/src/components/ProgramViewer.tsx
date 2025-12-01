'use client'

import { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'

interface ProgramViewerProps {
    content: string
}

interface ParsedSection {
    title: string
    content: string
}

export default function ProgramViewer({ content }: ProgramViewerProps) {
    const [parsedSections, setParsedSections] = useState<ParsedSection[]>([])
    const [activeTab, setActiveTab] = useState(0)

    useEffect(() => {
        if (!content) return
        const sections = parseProgramText(content)
        setParsedSections(sections)
        setActiveTab(0)
    }, [content])

    const parseProgramText = (text: string): ParsedSection[] => {
        // Split by "## Day" or "### Day"
        // Using lookahead to keep the delimiter in the split array logic
        // But simpler: split by regex and reconstruct

        // Regex to match the header: (##+ Day \d+.*)
        // We want to split but keep the header with the content.

        // Strategy:
        // 1. Split by the header pattern, capturing the header.
        // 2. Re-assemble.

        const dayRegex = /(#{2,3}\s*Day\s*\d+[^\n]*)/i
        const parts = text.split(dayRegex)

        const sections: ParsedSection[] = []

        // parts[0] is usually intro/overview (before first day)
        if (parts[0].trim()) {
            sections.push({
                title: "Overview",
                content: parts[0].trim()
            })
        }

        // The rest should be [Header, Content, Header, Content...]
        for (let i = 1; i < parts.length; i += 2) {
            const header = parts[i]
            const body = parts[i + 1] || ""

            // Extract "Day X" from header for the tab title
            const titleMatch = header.match(/Day\s*\d+/i)
            const title = titleMatch ? titleMatch[0] : "Day ?"

            sections.push({
                title: title,
                content: `${header}\n${body}`.trim()
            })
        }

        // Fallback: If no split happened (no "Day" headers found), show full text
        if (sections.length === 0 && content.trim()) {
            return [{ title: "Full Plan", content: content }]
        }

        return sections
    }

    if (!content) return null

    const showTabs = parsedSections.length > 1

    return (
        <div className="flex flex-col h-full">
            {/* Tabs */}
            {showTabs && (
                <div className="bg-zinc-900/50 border-b border-zinc-800 overflow-x-auto sticky top-0 z-10">
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
            <div className="flex-1 p-4">
                <div className="prose prose-invert prose-lg max-w-none">
                    <ReactMarkdown>
                        {parsedSections[activeTab]?.content || ""}
                    </ReactMarkdown>
                </div>
            </div>
        </div>
    )
}
