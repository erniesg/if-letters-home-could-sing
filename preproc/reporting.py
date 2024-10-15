from collections import Counter
from statistics import mean, median, stdev

def generate_summary_stats(char_counts, id_to_char):
    if not isinstance(char_counts, dict):
        raise ValueError("char_counts must be a dictionary")

    for char_id, counts in char_counts.items():
        if not isinstance(counts, dict):
            raise ValueError(f"Counts for character ID {char_id} must be a dictionary")
        for dataset, count in counts.items():
            if not isinstance(count, int) or count <= 0:
                raise ValueError(f"Count for character ID {char_id} in dataset {dataset} must be a positive integer")

    total_chars = sum(sum(counts.values()) for counts in char_counts.values())
    unique_chars = len(char_counts)

    counts_list = [count for counts in char_counts.values() for count in counts.values()]

    if not counts_list:
        return {
            "total_chars": 0,
            "unique_chars": 0,
            "avg_count": 0,
            "median_count": 0,
            "std_dev": 0,
            "most_common": [],
            "least_common": [],
            "gini": 0
        }

    avg_count = mean(counts_list)
    median_count = median(counts_list)
    std_dev = stdev(counts_list) if len(counts_list) > 1 else 0

    char_counter = Counter({char_id: sum(counts.values()) for char_id, counts in char_counts.items()})
    most_common = char_counter.most_common(5)
    least_common = char_counter.most_common()[:-6:-1]  # Get the 5 least common, reversed

    # Calculate Gini coefficient
    sorted_counts = sorted(counts_list)
    gini = sum(2 * i * count for i, count in enumerate(sorted_counts, 1)) / (len(sorted_counts) * sum(sorted_counts)) - (len(sorted_counts) + 1) / len(sorted_counts)

    return {
        "total_chars": total_chars,
        "unique_chars": unique_chars,
        "avg_count": avg_count,
        "median_count": median_count,
        "std_dev": std_dev,
        "most_common": [(id_to_char.get(char_id, char_id), count) for char_id, count in most_common],
        "least_common": [(id_to_char.get(char_id, char_id), count) for char_id, count in least_common],
        "gini": gini
    }

def print_summary_stats(stats):
    print(f"\nExtraction Summary:")
    print(f"Total characters extracted: {stats['total_chars']}")
    print(f"Unique characters: {stats['unique_chars']}")
    print(f"Average sample count: {stats['avg_count']:.2f}")
    print(f"Median sample count: {stats['median_count']}")
    print(f"Standard deviation: {stats['std_dev']:.2f}")
    print(f"\nMost common characters:")
    for char, count in stats['most_common']:
        print(f"  {char}: {count}")
    print(f"\nLeast common characters:")
    for char, count in stats['least_common']:
        print(f"  {char}: {count}")
    print(f"\nGini coefficient (measure of unbalancedness): {stats['gini']:.4f}")
