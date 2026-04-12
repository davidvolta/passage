#!/usr/bin/env python3
"""
extract_stories.py — Extract parables, koans, and stories from Osho books.

Reads from processed/markdown/*.md, uses narrative heuristics to identify stories,
and outputs them to stories.md organized by book.

Usage:
    python extract_stories.py
"""

import re
from pathlib import Path
from dataclasses import dataclass
from collections import Counter
from typing import List, Tuple, Dict, Any

# Configuration
MARKDOWN_DIR = Path("processed/markdown")
OUTPUT_FILE = Path("stories.md")
MIN_WORDS = 40
MAX_WORDS = 800


@dataclass
class Story:
    book_title: str
    book_slug: str
    text: str
    score: float
    indicators: List[str]


# Narrative indicators - past tense action verbs common in stories
NARRATIVE_VERBS = [
    'went', 'came', 'arrived', 'asked', 'said', 'replied', 'answered',
    'walked', 'sat', 'stood', 'looked', 'saw', 'found', 'lost', 'died',
    'lived', 'dropped', 'fell', 'rose', 'entered', 'left', 'returned',
    'called', 'cried', 'laughed', 'thought', 'felt', 'decided', 'began',
    'happened', 'occurred', 'passed', 'continued', 'stopped', 'remained',
    'prayed', 'meditated', 'realized', 'understood', 'awoke', 'slept',
    'opened', 'closed', 'took', 'gave', 'received', 'brought', 'carried',
    'killed', 'murdered', 'married', 'born', 'grew', 'became', 'turned',
    'knocked', 'climbed', 'ran', 'fled', 'chased', 'hid', 'appeared',
    'disappeared', 'waited', 'watched', 'listened', 'heard', 'spoke',
    'gathered', 'collected', 'created', 'made', 'built', 'destroyed',
    'bought', 'sold', 'paid', 'owed', 'stole', 'robbed', 'helped',
    'saved', 'rescued', 'threw', 'caught', 'hit', 'beat', 'kissed',
    'hugged', 'embraced', 'rejected', 'accepted', 'invited', 'visited',
]

# Character indicators
CHARACTERS = [
    'man', 'woman', 'child', 'boy', 'girl', 'king', 'queen', 'prince', 'princess',
    'monk', 'master', 'disciple', 'student', 'teacher', 'guru', 'sannyasin',
    'buddha', 'jesus', 'osho', 'mahavira', 'krishna', 'ramana', 'laotzu', 'chuangtzu',
    'boddhidharma', 'zen', 'sufi', 'rabbi', 'priest', 'bishop', 'pope',
    'emperor', 'soldier', 'warrior', 'general', 'merchant', 'farmer', 'beggar',
    'thief', 'robber', 'judge', 'lawyer', 'doctor', 'patient', 'fool', 'wise',
    'father', 'mother', 'brother', 'sister', 'son', 'daughter', 'husband', 'wife',
    'friend', 'enemy', 'stranger', 'villager', 'peasant', 'sage', 'saint',
    'mulla', 'nasrudin', 'junaid', 'baal', 'shem', 'rabiya', 'meera', 'kabir',
    'dogen', 'bokuju', 'joshu', 'ma tz', 'hyakujo', 'nansen', 'sekiso',
]

# Story opening patterns
OPENINGS = [
    r'\bonce\b',
    r'\bone day\b',
    r'\bone night\b',
    r'\bone morning\b',
    r'\bit happened\b',
    r'\bit is said\b',
    r'\bit is reported\b',
    r'\bthere was\b',
    r'\bthere lived\b',
    r'\bthere came\b',
    r'\ba long time ago\b',
    r'\blong ago\b',
    r'\bin the days\b',
    r'\bin ancient\b',
    r'\ba story\b',
    r'\bthe story\b',
    r'\bthe parable\b',
    r'\bthe koan\b',
    r'\ba man\s+',
    r'\ba woman\s+',
    r'\ba monk\s+',
    r'\ba king\s+',
    r'\ba queen\s+',
    r'\ba child\s+',
    r'\ba boy\s+',
    r'\ba girl\s+',
    r'\ban old\s+',
    r'\ban emperor\s+',
    r'\ba priest\s+',
    r'\ba rabbi\s+',
    r'\ba master\s+',
    r'\ba disciple\s+',
    r'\btwo men\b',
    r'\btwo women\b',
    r'\btwo monks\b',
    r'\btwo children\b',
    r'\btwo disciples\b',
    r'\ba rich\s+',
    r'\ba poor\s+',
    r'\ba young\s+',
    r'\ban elder\s+',
    r'\bmulla\s+nasrudin\b',
    r'\bbodhidharma\b',
    r'\bramana\b',
    r'\bzen\s+master',
    r'\bsufi\s+master',
    r'\ba traveler\b',
    r'\ba stranger\b',
    r'\ba beggar\b',
    r'\ba thief\b',
    r'\ba soldier\b',
    # New patterns from analysis
    r'\bonly a\s+',
    r'\bit is reported\b',
    r'\banother\s+',
    r'\bhe was\s+',
    r'\bshe was\s+',
    r'\bat one stage\b',
    r'\bat one point\b',
    r'\bthe young\s+',
    r'\bthe old\s+',
    r'\bwhen he\s+',
    r'\bwhen she\s+',
    r'\bjust think\b',
    r'\bit was\s+',
    r'\bbut one day\b',
    r'\bthere is\s+a\s+(story|sufi|zen|famous)',
    r'\bi have heard\b',
    r'\bi have known\b',
    r'\bto tell\s+you\s+a\s+story\b',
    r'\blet me tell\s+you\b',
]

# Dialogue indicators
DIALOGUE_PATTERNS = [
    r'"[^"]+"',  # Quotation marks
    r"'[^']+'",  # Single quotes
    r'\bsaid\b',
    r'\basked\b',
    r'\breplied\b',
    r'\banswered\b',
    r'\bcried\b',
    r'\bshouted\b',
    r'\bwhispered\b',
    r'\bmuttered\b',
    r'\bresponded\b',
    r'\bexclaimed\b',
]

# Story closings / morals
MORAL_INDICATORS = [
    r'\bthe moral\b',
    r'\blesson\b',
    r'\bthis is\s+',
    r'\bthis story\b',
    r'\bthe point\b',
    r'\bunderstand\s+this',
    r'\bremember\b',
]

# Anti-indicators (things that suggest NOT a story)
ANTI_INDICATORS = [
    r'^\d+\.',  # Numbered lists
    r'^\[',  # Editorial notes
    r'^chapter\s+\d+',  # Chapter headers
    r'^[a-z]+\s*:\s*',  # Speaker labels like "osho:"
    r'^[a-z\s]+talk[s]?$',  # Labels like "morning talk"
    r'^question\s*\d*',  # Question sections
    r'^answer[s]?$',  # Answer sections
    r'\?\s*$',  # Ends with question (probably a koan, but check context)
]


def count_word_frequencies(text: str) -> Counter:
    """Count word frequencies in text."""
    words = re.findall(r'\b[a-z]+\b', text.lower())
    return Counter(words)


def has_narrative_density(text: str) -> bool:
    """
    Check if first 2 sentences have at least 3 of 5 story elements:
    1. Past tense action verb
    2. Named character (he/she/name + title)
    3. Dialogue marker (said/asked/replied or quotes)
    4. Time/place setting (one day, there, in the, at the)
    5. Conflict or surprise (but, suddenly, however, shocked, surprised)
    """
    # Split into sentences (simple split on .!?)
    sentences = re.split(r'[.!?]+', text.lower())
    first_two = ' '.join(sentences[:2])

    elements_found = 0

    # 1. Past tense action verb
    past_verbs = ['went', 'came', 'arrived', 'asked', 'said', 'replied', 'walked',
                  'sat', 'stood', 'looked', 'saw', 'found', 'died', 'fell', 'rose',
                  'entered', 'left', 'returned', 'called', 'cried', 'laughed',
                  'began', 'happened', 'knocked', 'ran', 'fled', 'hid', 'appeared',
                  'waited', 'heard', 'spoke', 'took', 'gave', 'brought', 'killed',
                  'married', 'grew', 'became', 'turned', 'threw', 'caught', 'hit']
    if any(f' {v} ' in f' {first_two} ' for v in past_verbs):
        elements_found += 1

    # 2. Named character (he/she/they + was/had/said or proper name pattern)
    char_indicators = [' he ', ' she ', ' they ', ' a man ', ' a woman ', ' a monk ',
                       ' a king ', ' the king ', ' the master ', ' the disciple ']
    if any(c in first_two for c in char_indicators):
        elements_found += 1

    # 3. Dialogue marker
    dialogue_markers = ['"', "'", ' said ', ' asked ', ' replied ', ' answered ',
                        ' cried ', ' shouted ', ' shouted', ' told ']
    if any(d in first_two for d in dialogue_markers):
        elements_found += 1

    # 4. Time/place setting
    setting_markers = ['one day', 'one night', 'once ', 'there was', 'there lived',
                       'in the ', 'at the ', 'on the ', 'into the ', 'to the ']
    if any(s in first_two for s in setting_markers):
        elements_found += 1

    # 5. Conflict or surprise
    conflict_markers = ['but ', 'suddenly ', 'however ', 'shocked', 'surprised',
                        'afraid', 'worried', 'troubled', 'afraid', 'angry', 'fought',
                        'argued', 'refused', 'denied', 'against', 'enemy']
    if any(c in first_two for c in conflict_markers):
        elements_found += 1

    return elements_found >= 3


def score_paragraph(text: str) -> Tuple[float, List[str]]:
    """
    Score a paragraph for likelihood of being a story.
    Returns (score, list of matched indicators).
    """
    score = 0.0
    indicators = []
    text_lower = text.lower()
    words = text_lower.split()
    word_count = len(words)

    # Length check
    if word_count < MIN_WORDS or word_count > MAX_WORDS:
        return 0.0, []

    # Narrative density check - must have at least 3 story elements in first 2 sentences
    if not has_narrative_density(text):
        return 0.0, []

    # Anti-indicator check
    for pattern in ANTI_INDICATORS:
        if re.search(pattern, text_lower):
            return 0.0, []

    # Opening patterns (strong indicator)
    opening_matches = 0
    for pattern in OPENINGS:
        if re.search(pattern, text_lower):
            opening_matches += 1
            if opening_matches <= 3:  # Limit stored indicators
                indicators.append(f"opening:{pattern}")
    score += opening_matches * 3.0

    # Narrative verbs
    verb_count = sum(1 for verb in NARRATIVE_VERBS if f' {verb} ' in f' {text_lower} ')
    score += min(verb_count * 0.5, 5.0)  # Cap at 5 points
    if verb_count >= 3:
        indicators.append(f"verbs:{verb_count}")

    # Character references
    char_count = sum(1 for char in CHARACTERS if f' {char} ' in f' {text_lower} ')
    score += min(char_count * 1.0, 4.0)
    if char_count >= 1:
        indicators.append(f"characters:{char_count}")

    # Dialogue detection
    dialogue_matches = 0
    for pattern in DIALOGUE_PATTERNS:
        matches = len(re.findall(pattern, text_lower))
        dialogue_matches += matches
    score += min(dialogue_matches * 0.8, 4.0)
    if dialogue_matches >= 2:
        indicators.append(f"dialogue:{dialogue_matches}")

    # Story structure: temporal sequencing words
    sequence_words = ['then', 'after', 'before', 'when', 'while', 'suddenly',
                      'finally', 'eventually', 'later', 'soon', 'immediately',
                      'next', 'meanwhile', 'during', 'as soon as']
    seq_count = sum(1 for word in sequence_words if f' {word} ' in f' {text_lower} ')
    score += min(seq_count * 0.7, 3.0)
    if seq_count >= 2:
        indicators.append(f"sequence:{seq_count}")

    # Pronoun density (stories often have he/she/it/they)
    pronouns = ['he', 'she', 'they', 'him', 'her', 'them', 'his', 'their', 'it', 'its']
    pronoun_count = sum(1 for p in pronouns if f' {p} ' in f' {text_lower} ')
    if pronoun_count >= 3:
        score += 2.0
        indicators.append(f"pronouns:{pronoun_count}")

    # Direct address (you) suggests teaching, not story
    you_count = text_lower.count(' you ')
    if you_count > 5:
        score -= 2.0

    # Past tense density check
    past_tense_markers = ['was', 'were', 'had', 'did', 'said', 'went', 'came', 'saw', 'knew']
    past_count = sum(1 for p in past_tense_markers if f' {p} ' in f' {text_lower} ')
    if past_count >= 3:
        score += 2.0
        indicators.append(f"past_tense:{past_count}")

    # Story-specific phrases
    story_phrases = ['the end', 'and so', 'from that day', 'ever since', 'lived happily',
                     'lived forever', 'attained enlightenment', 'became enlightened',
                     'was silent', 'remained silent', 'started laughing', 'started crying',
                     'was surprised', 'was shocked', 'was amazed', 'was stunned']
    for phrase in story_phrases:
        if phrase in text_lower:
            score += 1.5
            indicators.append(f"phrase:{phrase}")

    # Zen/Sufi story patterns
    zen_patterns = [r'\bmaster\s+\w+\s+(said|asked|replied)',
                   r'\bdisciple\s+\w+\s+(said|asked|replied)',
                   r'\bthe\s+master\s+(was|remained)',
                   r'\benlightenment\b',
                   r'\bsatori\b',
                   r'\bsamadhi\b',
                   r'\bkoan\b',
                   r'\bzen\s+story\b',
                   r'\bsufi\s+story\b',]
    for pattern in zen_patterns:
        if re.search(pattern, text_lower):
            score += 1.0
            indicators.append("zen/sufi_pattern")

    # Quotation mark balance check (dialogue)
    double_quotes = text.count('"')
    single_quotes = text.count("'")
    if double_quotes >= 2 and double_quotes % 2 == 0:
        score += 1.5
        indicators.append("quoted_dialogue")
    elif single_quotes >= 2 and single_quotes % 2 == 0:
        score += 1.0
        indicators.append("quoted_dialogue")

    # Negatives for abstract/philosophical content
    abstract_words = ['philosophy', 'philosophical', 'theory', 'concept', 'abstract',
                      'ideology', 'doctrine', 'principle', 'fundamental', 'essentially',
                      'basically', 'in fact', 'the fact is', 'the truth is']
    abstract_count = sum(1 for w in abstract_words if f' {w} ' in f' {text_lower} ')
    score -= abstract_count * 0.5

    return score, indicators


def parse_frontmatter(md_content: str) -> Tuple[Dict, str]:
    """Extract YAML frontmatter and body from markdown."""
    if not md_content.startswith("---"):
        return {"title": "Unknown"}, md_content

    parts = md_content.split("---", 2)
    if len(parts) < 3:
        return {"title": "Unknown"}, md_content

    # Simple frontmatter parsing without yaml dependency
    metadata: Dict[str, str] = {}
    for line in parts[1].strip().split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            metadata[key.strip()] = value.strip().strip('"').strip("'")

    body = parts[2].strip()
    return metadata, body


def extract_stories_from_file(md_path: Path) -> List[Story]:
    """Extract stories from a single markdown file."""
    stories = []

    try:
        md_content = md_path.read_text(encoding="utf-8")
        metadata, body = parse_frontmatter(md_content)

        book_title = metadata.get("title", md_path.stem.replace("-", " ").title())
        book_slug = metadata.get("slug", md_path.stem)

        # Split into paragraphs
        paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]

        print(f"\n📖 {book_title}")
        print(f"   {len(paragraphs)} paragraphs")

        for para in paragraphs:
            # Skip clearly non-content
            if para.startswith('[') and para.endswith(']'):
                continue
            if len(para) < 100:
                continue

            score, indicators = score_paragraph(para)

            # Threshold for story detection (high quality only)
            if score >= 10.0:
                stories.append(Story(
                    book_title=book_title,
                    book_slug=book_slug,
                    text=para,
                    score=score,
                    indicators=indicators[:5]  # Top 5 indicators
                ))

        print(f"   → Found {len(stories)} stories (score >= 10.0)")
        return stories

    except Exception as e:
        print(f"Error processing {md_path.name}: {e}")
        return []


def write_stories_md(stories: List[Story], output_path: Path):
    """Write extracted stories to markdown file."""

    # Sort by book, then by score (highest first)
    stories.sort(key=lambda s: (s.book_title, -s.score))

    # Group by book
    by_book: Dict[str, List[Story]] = {}
    for story in stories:
        by_book.setdefault(story.book_title, []).append(story)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# Osho Stories, Parables, and Koans\n\n")
        f.write(
            "*A collection of narrative teachings extracted from Osho's talks*\n\n"
        )
        f.write(f"**Total stories:** {len(stories)}\n\n")
        f.write("---\n\n")

        for book_title in sorted(by_book.keys()):
            book_stories = by_book[book_title]
            f.write(f"## {book_title}\n\n")

            for i, story in enumerate(book_stories, 1):
                f.write(f"### {i}. (score: {story.score:.1f})\n\n")
                f.write(f"{story.text}\n\n")

                # Add indicators for debugging/verification
                if story.indicators:
                    f.write(f"*Indicators: {', '.join(story.indicators)}*\n\n")
                f.write("---\n\n")

    print(f"\n✅ Wrote {len(stories)} stories to {output_path}")


def main():
    md_files = sorted(MARKDOWN_DIR.glob("*.md"))
    if not md_files:
        print(f"No markdown files found in {MARKDOWN_DIR}")
        return

    # Process all files
    print(f"Processing {len(md_files)} books")

    all_stories = []

    for md_path in md_files:
        stories = extract_stories_from_file(md_path)
        all_stories.extend(stories)

    if all_stories:
        write_stories_md(all_stories, OUTPUT_FILE)
        print(f"\n📚 Extracted {len(all_stories)} total stories from {len(md_files)} books")

        # Show score distribution
        scores = [s.score for s in all_stories]
        print(f"\nScore distribution:")
        print(f"  High (10+): {len([s for s in scores if s >= 10])}")
        print(f"  Medium (7-9.9): {len([s for s in scores if 7 <= s < 10])}")
        print(f"  Low (6-6.9): {len([s for s in scores if s < 7])}")
    else:
        print("\nNo stories found.")


if __name__ == "__main__":
    main()
