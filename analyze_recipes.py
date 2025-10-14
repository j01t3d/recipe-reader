import os, re
from collections import Counter
import matplotlib.pyplot as plt
import numpy as np
import time

from threading import Lock

THREADS = 5

# lock = Lock()

def get_words_from_folder(folder):
    startTime = time.time()
    words = []
    texts = []
    for filename in os.listdir(folder):
        if filename.endswith(".txt"):
            with open(os.path.join(folder, filename), "r", encoding="utf-8") as f:
                text = f.read().lower()
                texts.append(text)
                tokens = re.findall(r"[a-z']+", text)
                words.extend(tokens)
    endTime = time.time()
    print("Time taken to merge words: ", endTime - startTime, " second(s) spent in folder ", folder)
    return words, texts

def count_top_keywords_in_text(texts, top_keywords):
    startTime = time.time()
    counts_per_file = []
    for text in texts:
        tokens = set(re.findall(r"[a-z']+", text))
        count = sum(1 for kw in top_keywords if kw in tokens)
        counts_per_file.append(count)
    endTime = time.time()
    print("Time taken to count top keywords: ", endTime - startTime, " second(s)")
    return counts_per_file

def main():
    # load text
    recipe_words, recipe_texts = get_words_from_folder("recipes")
    nonrecipe_words, nonrecipe_texts = get_words_from_folder("nonrecipes")

    # count word frequencies
    recipe_counts = Counter(recipe_words)
    nonrecipe_counts = Counter(nonrecipe_words)

    # remove common stopwords and short words
    stopwords = {"the","and","of","to","a","in","for","on","is","at","it","this","that","with","by","from"}
    for w in list(recipe_counts):
        if w in stopwords or len(w) < 3:
            del recipe_counts[w]

    # find words that are common in recipes but rare in nonrecipes
    distinctive = {w: c for w, c in recipe_counts.items() if nonrecipe_counts[w] < 5}

    # top keywords
    top_keywords = [w for w, c in Counter(distinctive).most_common(100)]

    print("\nTop 100 likely recipe keywords:\n")
    for w, c in Counter(distinctive).most_common(100):
        print(f"{w}: {c}")

    # count top keywords per file
    recipe_counts_per_file = count_top_keywords_in_text(recipe_texts, top_keywords)
    nonrecipe_counts_per_file = count_top_keywords_in_text(nonrecipe_texts, top_keywords)

    # print stats
    def stats(name, counts):
        counts_np = np.array(counts)
        print(f"\n{name}:")
        print(f"  Avg: {counts_np.mean():.1f}")
        print(f"  Median: {np.median(counts_np)}")
        print(f"  Min: {counts_np.min()}")
        print(f"  Max: {counts_np.max()}")

    stats("Recipes", recipe_counts_per_file)
    stats("Nonrecipes", nonrecipe_counts_per_file)

    # plot on graph
    plt.figure(figsize=(10,6))
    plt.hist(recipe_counts_per_file, bins=range(0, max(recipe_counts_per_file)+2), alpha=0.7, label='Recipes')
    plt.hist(nonrecipe_counts_per_file, bins=range(0, max(recipe_counts_per_file)+2), alpha=0.7, label='Non-recipes')
    plt.xlabel("Number of top 100 keywords per file")
    plt.ylabel("Number of files (logarithmic)")
    plt.title("Distribution of Top 100 Recipe Keywords in Files")
    plt.legend()
    plt.grid(axis='y')
    plt.yscale('log')
    plt.show()

if __name__ == "__main__":
    main()
