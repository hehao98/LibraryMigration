# Library Migration

This repository will be our main repository for our ongoing empirical paper about Java library migrations.
Note that for easy release and disposal in the future, we demand everything here must be written in English.
All files should not have any names so that we can just remove version control info for double blind review.

## Development

We use Anaconda and PyCharm Professional for development. 
Please configure your PyCharm to use a new Conda environment with Python 3.7+ and [requirements](requirements.txt) satisfied.

## Data Preparation

A dataset of library migration is already available [here](data/migrations.xlsx).
The more compact dataset of legal library migration rules is [here](data/rules.xlsx).
We use [get_issues.py](get_prs_by_commits.py) Python script to get issues and PRs [here](data/prs.xlsx).
We then use [get_coding_data.py](get_coding_data.py) to aggregate coding data [here](data/coding_commits_prs.xlsx).

## Thematic Analysis

[1] provides an in-depth introduction to thematic analysis.

### Possible RQs

Canonically, a round of thematic analysis should only deals with one RQ.
However, since we do not know our RQ exactly now,
we seek to answer these possible research questions through this thematic analysis.
* What are the reasons for a library migration? 
* How is a library migration decided? 
* How is a migration target chosen? 
* Who decides a library migration? 
* Who cares about library migrations?

### Important Concepts

1. **Code**. A code identifies or provides a label for a feature of data that is *potentially* relevant to the RQs.
2. **Theme**. A theme captures something important about the data in relation to the RQs, 
and represents some level of *patterned* response or meaning with in the dataset.

### Phases

1. Familiarize with the data by reading and re-reading them.
2. Generate initial code (must be relevant to RQ, inclusive, thorough and systematic).
3. Searching for themes. A theme should be clear/independent but themes should also tell a good story as a whole.
4. Reviewing potential themes. Amount of evidence, relevance to RQ, boundary, coherence.
5. Defining and naming themes (and/or sub-themes). Answering "So what?".
6. Producing the report.

### Text for Analysis

We have three kind of text to analyze: commit messages, issues, and PRs.
For issues and PRs, we analyze all text in the issue/PR page, including titles, descriptions, and comments.
If some clearly relevant link is identified, we add the text in the links to our data as well. 
Since most of the text may be irrelevant, two of the authors should independently collect and keep relevant raw text in two table sheets in Phase 1.

## References

1. Braun, Virginia, and Victoria Clarke. "Thematic analysis." (2012). [Download](https://www.researchgate.net/profile/David_Morgan19/post/how_to_do_qualitative_analysis_of_25_one_to_one_interviews/attachment/5b045e3f4cde260d15e0492e/AS%3A629151971151872%401527012927043/download/Braun+12+Psych+Handbook.pdf)

