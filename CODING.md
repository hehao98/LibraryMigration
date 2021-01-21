# Reasons for a Library Migration

## Data Preparation

A dataset of library migration is already available [here](data/migrations.xlsx).
The more compact dataset of legal library migration rules is [here](data/rules.xlsx).
We use [get_issues.py](get_prs_by_commits.py) Python script to get issues and PRs [here](data/prs.xlsx).
We then use [get_coding_data.py](get_coding_data.py) to aggregate coding data [here](data/coding_commits_prs.xlsx).

The final coding is done entirely manually in [this file](data/coding.xlsx).

## Thematic Analysis

[1] provides an in-depth introduction to thematic analysis. 
[2] provides specific clarifications in the context of software engineering. 
Read through them if you haven't done so.

### Research Questions

Canonically, a round of thematic analysis should only deals with one RQ.
We seek to answer this possible research question throughout this thematic analysis:
**What are the reasons for a library migration?**

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

## Generated Codes

### Source Library

1. **No Longer Maintained**. (`source:no-longer-maintained`) The text mentions that the source library is no longer maintained, deprecated, end-of-life, etc. Since the source library will have no further fixes and security patches, it makes sense to move away from this library.
2. **Outdated**. (`source:outdated`) The text states that the source library is old, outdated, obsolete. The source library may still have some maintenance but the project abandon it because there are more "modern" choices, which may fit better with recently emerged requirements.
3. **Vulnerability**. (`source:vulnerability`) The text states that the source library has security vulnerability (CVE). We distinguish this from other issues because it is more common and probably more important than other issues when maintaining dependencies.
4. **Issue**. (`source:issue`) The text states that the developers encountered a bug, warning, error or other issues with the source library. The issue is mainly from the library itself and not the result of interaction with other project contextual factors.

### Target Library

1. **Feature**. (`target:feature`) The text states that the target library has some desirable feature for the project.
2. **Ease of Use**. (`target:ease-of-use`) The text conveys that the target library is more convinient to use, results in cleaner code, easy to configure, etc.
3. **Performance**. (`target:performance`) The text states that the target library runs faster, is memory efficient, has smaller size, or is lightweight.
4. **Flexibility**. (`target:flexibility`) The text states that the target library is more flexible, allow user to choose inner implementation, etc.

### Project Specific

The main difference between **Consistency** and **Compatibility** is that, the former is to adopt a consistent practice for reducing further maintanance effort, while the latter is to take immediate action to solve a specific problem.

1. **Compatibility - License**. (`project:compatibility:license`) The text discusses license issues of the source library. However, license only becomes a problem when a project meets some of the license restrictions, so we put it into *Project Context* Category.
2. **Compatibility - Other Library**. (`project:compatibility:other-library`)  The text states that developers conduct the migration because the target library is better integrated with another library the project is using.
3. **Compatibility - Environment**. (`project:compatibility:environment`) The text states that developers conduct the migration because the target library is better integrated with project development or runtime environment (OS, JRE, CI, etc).
4. **Consistency - with Upstream**. (`project:consistency:upstream`) The text states that the project align library choices with other libraries or frameworks the project is already using and likely deeply integrated. For example, a project may choose to use `jackson` because Spring is already using it and the project is deeply integrated with Spring.
5. **Consistency - with Downstream**. (`project:consistency:downstream`) The text indicates a request from downstream users to migrate to a library because they are already using it.
6. **Consistency - within Project**. (`project:consistency:within-project`) The text states that the migration is done to achieve consistency of practices within a project. The most common cases are using one library for one functionality instead of using different libraries in different modules to do the same thing. In other cases, migration is done for consistency in code or configuration.
7. **Organizational Influence**. (`project:organizational`) The organization enforces a rule, or recommend to not use the source library or to use the target library.
8. **Other**. (`project:other`) Other project specifc reasons which cannot be put in any of the above taxonomies, e.g. reduce JAR size, reduce number of dependencies.

### Library Specfic - Another Alternative

The following categories are adopted from [3] but does not seem to fit well because some reasons are rather common in the context of library migration.

1. **Feature**.
2. **Usability**.
3. **Performance**.
4. **Security**.
5. **Activity**.
6. **Size/Complexity**.
7. **Stability/Maturity**.

## References

1. Braun, Virginia, and Victoria Clarke. "Thematic analysis." (2012). 
   [Download](https://www.researchgate.net/profile/David_Morgan19/post/how_to_do_qualitative_analysis_of_25_one_to_one_interviews/attachment/5b045e3f4cde260d15e0492e/AS%3A629151971151872%401527012927043/download/Braun+12+Psych+Handbook.pdf)
2. Cruzes, Daniela S., and Tore Dyba. "Recommended steps for thematic synthesis in software engineering." 
   2011 international symposium on empirical software engineering and measurement. IEEE, 2011.
3. Larios-Vargas, Enrique, et al. "Selecting third-party libraries: The practitioners' perspective." arXiv preprint arXiv:2005.12574 (2020).
