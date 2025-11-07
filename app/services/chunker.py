from typing import List, Dict
import tiktoken
import re

class SemanticChunker:
    """Chunk documents using semantic boundaries where possible."""

    def __init__(self, chunk_size: int = 300, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap
        # Use OpenAI's tiktoken to count tokens.
        self.encoder = tiktoken.get_encoding("cl100k_base")

    def chunk_document(self, text: str, metadata: Dict) -> List[Dict]:
        """Produce chunks from a document respecting semantic boundaries."""
        sections = self._detect_sections(text)
        chunks = []
        for section in sections:
            if self._is_atomic_section(section):
                chunks.append(self._create_chunk(section, metadata))
            else:
                sub_chunks = self._split_with_overlap(section, self.chunk_size, self.overlap)
                chunks.extend([self._create_chunk(chunk, metadata) for chunk in sub_chunks])
        return chunks

    def _detect_sections(self, text: str) -> List[str]:
        """
        Heuristiques de découpe orientées documents :
        - Titres (niveaux Markdown, lignes MAJUSCULES, numérotation 1., 1.1., etc.)
        - Sections connues du domaine (Exemples, Consignes, Erreurs fréquentes, Variantes, Matériel)
        - Listes à puces / numérotées
        Retour: liste de paragraphes (strings) prêts pour le token-splitting
        """
        lines = [ln.strip() for ln in text.splitlines()]
        blocks, buf = [], []

        title_re = re.compile(r'^(#{1,6}\s+.+|[A-Z0-9][A-Z0-9 \-/]{6,}|(?:\d+\.)+\s+.+)$')
        domain_re = re.compile(r'^(exemples?|consignes?|erreurs? fréquentes?|variantes?|matériel|equipement|équipement)\s*:?\s*$', re.I)
        bullet_re = re.compile(r'^(\-|\*|\d+\)|\d+\.)\s+')

        def flush():
            if buf:
                blocks.append("\n".join(buf).strip())
                buf.clear()

        for ln in lines:
            if not ln:
                flush()
                continue

            # Hard boundary on titles or section headers
            if title_re.match(ln) or domain_re.match(ln):
                flush()
                blocks.append(ln)
                continue

            # Keep list items grouped but allow paragraph boundaries on blank lines
            if bullet_re.match(ln):
                buf.append(ln)
                continue

            buf.append(ln)

        flush()
        # Filtrer les vides
        return [b for b in blocks if b and len(b) > 1]

    def _is_atomic_section(self, section: str) -> bool:
        """Heuristically decide whether a section is small enough to keep intact."""
        tokens = self.encoder.encode(section)
        return len(tokens) <= self.chunk_size

    def _split_with_overlap(self, text: str, size: int, overlap: int) -> List[str]:
        tokens = self.encoder.encode(text)
        chunks = []
        for i in range(0, len(tokens), size - overlap):
            chunk_tokens = tokens[i:i + size]
            chunks.append(self.encoder.decode(chunk_tokens))
        return chunks

    def _create_chunk(self, text: str, metadata: Dict) -> Dict:
        return {
            "text": text,
            "metadata": {
                **metadata,
                "chunk_size": len(self.encoder.encode(text)),
                "preview": text[:100] + "..."
            }
        }