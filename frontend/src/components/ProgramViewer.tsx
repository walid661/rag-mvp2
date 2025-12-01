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
        // Regex to match "Day X" headers with or without markdown (##)
        // We use a regex that looks for the pattern at the start of a line
        // Regex: ((?:^|\n)(?:#{0,3}\s*)Day\s*\d+[^\n]*)
        // This captures the entire header line.
        const splitRegex = /((?:^|\n)(?:#{0,3}\s*)Day\s*\d+[^\n]*)/i
        const parts = text.split(splitRegex)

        const sections: ParsedSection[] = []

        // parts[0] = Overview (or empty)
        // parts[1] = Header 1
        // parts[2] = Content 1

        if (parts[0].trim()) {
            sections.push({
                title: "Overview",
                content: parts[0].trim()
            })
        }

        for (let i = 1; i < parts.length; i += 2) {
            const headerLine = parts[i]
            const body = parts[i + 1] || ""

            // Extract "Day X" for the tab title
            const dayMatch = headerLine.match(/Day\s*\d+/i)
            const title = dayMatch ? dayMatch[0] : "Day ?"

            // Clean up the header line (remove leading newlines if split captured them)
            const cleanHeader = headerLine.replace(/^\n/, '')

            sections.push({
                title: title,
                content: `${cleanHeader}${body}`.trim()
            })
        }

        // Fallback
        if (sections.length === 0 && text.trim()) {
            return [{ title: "Full Plan", content: text }]
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
