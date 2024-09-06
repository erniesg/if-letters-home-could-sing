import os
import unicodedata
from fontTools.ttLib import TTFont
from collections import defaultdict

def get_unique_chars(file_path):
    encodings = ['utf-8', 'utf-16', 'gb18030']
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as file:
                text = file.read()
            return set(char for char in text if unicodedata.category(char)[0] not in ['C', 'Z'])
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Unable to decode the file with encodings: {encodings}")

def check_font_coverage(fonts, chars):
    coverage = defaultdict(set)
    for font_path in fonts:
        try:
            font = TTFont(font_path, fontNumber=0)
            for char in chars:
                for cmap in font['cmap'].tables:
                    if cmap.isUnicode():
                        if ord(char) in cmap.cmap:
                            coverage[font_path].add(char)
        except Exception as e:
            print(f"Error processing font {font_path}: {e}")
    return coverage

def analyze_fonts(file_path):
    unique_chars = get_unique_chars(file_path)
    print(f"Total unique characters: {len(unique_chars)}")

    # Get all font files on your system (this path is for macOS)
    font_dirs = ['/System/Library/Fonts', '/Library/Fonts', os.path.expanduser('~/Library/Fonts')]
    font_paths = []
    for font_dir in font_dirs:
        if os.path.exists(font_dir):
            font_paths.extend([os.path.join(font_dir, f) for f in os.listdir(font_dir) if f.endswith(('.ttf', '.otf'))])

    # Exclude LastResort.otf
    font_paths = [f for f in font_paths if 'LastResort.otf' not in f]

    coverage = check_font_coverage(font_paths, unique_chars)

    # Sort fonts by coverage
    sorted_fonts = sorted(coverage.items(), key=lambda x: len(x[1]), reverse=True)

    print("\nFont Coverage:")
    for font, chars in sorted_fonts:
        print(f"{os.path.basename(font)}: {len(chars)}/{len(unique_chars)} ({len(chars)/len(unique_chars)*100:.2f}%)")

    best_font = sorted_fonts[0][0]
    print(f"\nBest font: {os.path.basename(best_font)}")
    print(f"Characters covered by best font: {len(coverage[best_font])}/{len(unique_chars)} ({len(coverage[best_font])/len(unique_chars)*100:.2f}%)")

    # Find characters not covered by any font
    all_covered = set.union(*coverage.values())
    uncovered = unique_chars - all_covered
    if uncovered:
        print("\nCharacters not covered by any font:")
        for char in sorted(uncovered):
            print(f"U+{ord(char):04X}: {char}")
    else:
        print("\nAll characters are covered by at least one font.")

    return unique_chars, coverage

if __name__ == "__main__":
    file_path = input("Enter the path to your text file: ")
    unique_chars, coverage = analyze_fonts(file_path)

    # Optional: Save results to a file
    with open('font_analysis_results.txt', 'w', encoding='utf-8') as f:
        f.write(f"Total unique characters: {len(unique_chars)}\n\n")
        f.write("Font Coverage:\n")
        for font, chars in sorted(coverage.items(), key=lambda x: len(x[1]), reverse=True):
            f.write(f"{os.path.basename(font)}: {len(chars)}/{len(unique_chars)} ({len(chars)/len(unique_chars)*100:.2f}%)\n")

        all_covered = set.union(*coverage.values())
        uncovered = unique_chars - all_covered
        if uncovered:
            f.write("\nCharacters not covered by any font:\n")
            for char in sorted(uncovered):
                f.write(f"U+{ord(char):04X}: {char}\n")
        else:
            f.write("\nAll characters are covered by at least one font.\n")

    print("\nDetailed results have been saved to 'font_analysis_results.txt'")
