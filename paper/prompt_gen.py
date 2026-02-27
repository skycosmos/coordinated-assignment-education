# -------------------------------------- #
def generate_combined_paper_analysis_prompt() -> str:
    """
    Generate a combined prompt for extracting both paper metadata and CCAS information in one call.
    This saves tokens by combining two analyses into a single API call.
    
    Returns:
        str: System prompt for combined paper analysis
    """
    
    prompt_text = """
You are an education policy researcher analyzing academic papers about school choice and student assignment systems.
Your task is to extract BOTH basic paper metadata AND detailed CCAS information from the provided paper text.
The paper may discuss multiple cities, regions, or countries, or may contain no relevant assignment system information.

### PART 1: PAPER METADATA EXTRACTION

Extract the following basic information from the paper:

1. **Title**: Title of the paper
2. **Year**: Year of publication (4-digit number or "Unknown")
3. **Authors**: List of authors in "Last Name, First Name" format, separated by commas
4. **Summary**: Comprehensive summary of main contributions and findings (max 400 words)
5. **Relevance**: Relevance score (provide ONLY the number):
   - 3 = Highly Related (main focus on coordinated choice and assignment systems)
   - 2 = Moderately Related (describes systems but not main focus)
   - 1 = Barely Related (mentions systems but focuses on other topics)
   - 0 = Not Related (completely unrelated to assignment systems)

### PART 2: CCAS SYSTEM INFORMATION EXTRACTION

For each region/city discussed in the paper, extract:

**Key Definition**: A system is **Coordinated** if ALL hold: (1) Applicants submit ranked preferences, (2) External authority partially/fully determines enrollment, (3) Centralized algorithm generates single offer. Otherwise it is **Uncoordinated**.

**Extract these attributes**:
- **Region**: City, Region, or Country name
- **ISO3 Country Code**: Three-letter code (e.g., SGP, CHN) or "Unknown"
- **Education Level**: Only ONE of: Pre-Primary, Primary, Secondary, Tertiary, Unknown
- **CCAS Status**: Coordinated, Uncoordinated, or Unknown
- **Participating Institutions**: Public, Private, Both, or Unknown
- **Preference List Length**: Maximum number of preferences applicants can rank or "Unknown"
- **Priority Criteria**: Factors in assignment (academic, distance, family, sen, gender, ses, sibling, diversity, zone, rural, religion, race, alumni, incumbent, population, field, gifted, time, other, Unknown)
- **Assignment Mechanism**: Immediate Acceptance, Deferred Acceptance, Serial Dictatorship, Top Trading Cycles, Other, or Unknown
- **Adoption Year**: Year first CCAS implemented or "Unknown"
- **Reform Year**: Year of most recent major reform or "Unknown"
- **Notes**: Summary of system description and any caveats (max 250 words)

### OUTPUT FORMAT (JSON ONLY)

Return valid JSON (no markdown or commentary) with this structure:

{
    "paper_metadata": {
        "title": "...",
        "year": "...",
        "authors": "...",
        "summary": "...",
        "relevance": "..."
    },
    "ccas_systems": [
        {
            "region": "...",
            "iso3_country_code": "...",
            "education_level": "...",
            "ccas_status": "...",
            "participating_institutions": "...",
            "preference_list_length": "...",
            "priority_criteria": ["..."],
            "assignment_mechanism": "...",
            "adoption_year": "...",
            "reform_year": "...",
            "notes": "..."
        }
    ]
}

### CRITICAL RULES

1. **Multiple education levels**: If the paper discusses multiple levels for the same region, return separate objects in ccas_systems array
2. **CCAS Cascade Rule**: If ccas_status is "Uncoordinated" or "Unknown", set these to "Unknown": participating_institutions, preference_list_length, priority_criteria, assignment_mechanism, adoption_year, reform_year. Only notes should explain.
3. **No fabrication**: Use "Unknown" if information is not found. Do NOT invent facts.
4. **Priority Criteria**: Return as array. Include all criteria mentioned. Return ["Unknown"] if none mentioned.
5. **Empty systems**: If paper discusses no assignment systems, return empty ccas_systems array: []
6. **Relevance**: Only the number (0, 1, 2, or 3)
7. **JSON only**: No markdown, no extra commentary, just valid JSON

### EXAMPLE OUTPUT:

{
    "paper_metadata": {
        "title": "The Boston School Choice Mechanism",
        "year": "2005",
        "authors": "Abdulkadiroğlu, Atila; Sönmez, Tayfun",
        "summary": "This paper analyzes the Boston Public Schools assignment mechanism implemented in 1999...",
        "relevance": "3"
    },
    "ccas_systems": [
        {
            "region": "Boston, Massachusetts",
            "iso3_country_code": "USA",
            "education_level": "Secondary",
            "ccas_status": "Coordinated",
            "participating_institutions": "Public",
            "preference_list_length": 3,
            "priority_criteria": ["sibling", "zone"],
            "assignment_mechanism": "Immediate Acceptance",
            "adoption_year": 1999,
            "reform_year": 2005,
            "notes": "Boston uses the Boston Mechanism where students rank schools..."
        }
    ]
}
"""
    return prompt_text


# -------------------------------------- #
def generate_paper_metadata_prompt() -> str:
    """
    Generate a prompt for extracting basic metadata from academic papers.
    Extracts title, year, authors, summary, and relevance to CCAS research.
    
    Returns:
        str: System prompt for paper metadata extraction
    """
    
    prompt_text = """
You are an education policy researcher analyzing academic papers related to school choice and student assignment systems.
Your task is to extract basic metadata and relevance information from the provided paper text.

### Instructions
Extract the following information from the paper and provide each answer within curly braces {}:

1. **Title**: {Title of the paper}
2. **Year**: {Year of publication - provide as a 4-digit number or "Unknown"}
3. **Authors**: {List of authors in "Last Name, First Name" format, separated by commas, or "Unknown"}
4. **Summary**: {Comprehensive summary of the paper's main contributions and findings (maximum 400 words)}
5. **Relevance**: {Only provide the number:
   3 = Highly Related: The paper's main focus is to analyze coordinated choice and assignment systems or their core components
   2 = Moderately Related: The paper describes coordinated assignment systems or components but they are not the main focus
   1 = Barely Related: The paper mentions coordinated assignment systems or components but focuses primarily on other topics
   0 = Not Related: The paper is completely unrelated to assignment systems or choice mechanisms}

### Output Format
Provide your response in the following format with each answer within curly braces:

1. Title: {your answer}
2. Year: {your answer}
3. Authors: {your answer}
4. Summary: {your answer}
5. Relevance: {your answer}

### Important Notes
- If any information is not available in the paper, use "Unknown"
- Do NOT invent or guess information
- For relevance, provide ONLY the number (0, 1, 2, or 3), not the description
- Ensure all responses are within the curly braces {}
"""
    return prompt_text


# -------------------------------------- #
def generate_ccas_extraction_prompt() -> str:
    """
    Generate a prompt for extracting centralized admission and assignment system information from academic papers.
    Designed to handle multiple regions/cities mentioned in a paper and gracefully handle missing or incomplete information.
    
    Returns:
        str: System prompt for CCAS extraction from academic papers
    """
    
    prompt_text = """
You are an education policy researcher specializing in school choice and student assignment systems.
Your task is to extract information about **centralized admission and assignment systems** from the provided academic paper text.
The paper may discuss multiple cities, administrative regions, or countries, or may contain no relevant information.

### Key Definitions
A system is **Coordinated** if ALL of the following conditions hold:
1. Applicants submit a ranked list of preferences
2. A group of institutions have enrollment partially or fully determined by an external authority
3. Each applicant receives a single offer generated by a centralized algorithm
Otherwise, classify it as **Uncoordinated**.

### Attributes to Extract (for each region/city mentioned):

- **CCAS Status**: Whether the region operates a Coordinated Choice and Assignment System. Values: Coordinated, Uncoordinated, or Unknown.
- **ISO3 Country Code**: Three-letter ISO 3166-1 alpha-3 country code (e.g., "SGP" for Singapore, "CHN" for China).
- **Education Level**: The level of education covered by the system. Choose ONE: pre-primary, primary, secondary, or tertiary. If the paper discusses multiple education levels, create separate JSON objects for each level.
- **Preference List Length**: The maximum number of institutions an applicant can rank. If no limit exists or no preference list is mentioned, return "Unknown".
- **Priority Criteria**: Factors considered in assigning students (e.g., academic performance, distance, socioeconomic equity). See abbreviations below.
- **Assignment Mechanism**: Algorithm used to match students (e.g., Immediate Acceptance, Deferred Acceptance, Serial Dictatorship, Top Trading Cycles).
- **Adoption Year**: Year the first CCAS was implemented. Return "Unknown" if not mentioned.
- **Reform Year**: Year of most recent major CCAS reform. Return adoption year if no reforms mentioned.

### Priority Criteria Abbreviations:
- "academic": Academic performance
- "distance": Transportation or distance to school
- "family": Parental employment or parental needs
- "sen": Special educational needs
- "gender": Gender equity
- "ses": Socioeconomic equity
- "sibling": Sibling priority
- "diversity": Diversity quota
- "zone": Zone or neighborhood priority
- "rural": Rural area
- "religion": Religious priority
- "race": Racial or Indigenous quota
- "alumni": Former student in institution
- "incumbent": Currently enrolled student
- "population": Population-based criteria
- "field": Specific field study
- "gifted": Gifted applicants
- "time": Waiting time
- "other": Other criteria not listed above
- "Unknown": No criteria mentioned

### Assignment Mechanisms:
- "Immediate Acceptance": Boston Mechanism; single round assignment
- "Deferred Acceptance": Tentative assignment with reassignments until stable match
- "Serial Dictatorship": Ordered applicants select in turn
- "Top Trading Cycles": Cycle-based exchanges until all assigned
- "Other": Any other mechanism not listed above
- "Unknown": Not specified

### Output Format (JSON only)

Return a JSON object (or array of objects if multiple regions/education levels are discussed) with fields:
{
    "region": "City, Region, or Country name (or 'Not specified' if unclear)",
    "iso3_country_code": "Three-letter ISO 3166-1 alpha-3 code (e.g., 'SGP', 'CHN', 'Unknown')",
    "education_level": "Pre-Primary | Primary | Secondary | Tertiary | Unknown",
    "ccas_status": "Coordinated | Uncoordinated | Unknown",
    "participating_institutions": "Public | Private | Both | Unknown",
    "preference_list_length": "Number or Unknown",
    "priority_criteria": ["list of criteria codes"],
    "assignment_mechanism": "Mechanism or Unknown",
    "adoption_year": "Number or Unknown",
    "reform_year": "Number or Unknown",
    "notes": "Summary (< 250 words) of the admission system description, caveats, or data quality issues"
}

### Rules:
- **Multiple regions and education levels**: If the paper discusses multiple cities/regions or multiple education levels, return an array of JSON objects. Each object represents ONE region-education_level combination.
- **Education level per object**: Each JSON object must have only ONE education_level value (pre-primary, primary, secondary, or tertiary). If a paper discusses pre-primary AND primary education for the same region, return two separate JSON objects.
- **CCAS status cascade**: If ccas_status is "Uncoordinated" or "Unknown", set ALL following fields to "Unknown" (except notes): participating_institutions, preference_list_length, priority_criteria, assignment_mechanism, adoption_year, reform_year. Only notes should contain an explanation.
- **Coordinated vs. Uncoordinated**: If no coordinated system is mentioned for a region, set ccas_status to "Uncoordinated" (unless explicitly stated differently).
- **Unknown vs. Absent**: Use "Unknown" only when the paper DISCUSSES the system but information is incomplete.
- **Do NOT invent facts**: If no credible information is found in the paper, return "Unknown" and explain in notes.
- **Priority Criteria**: Return an array. If multiple criteria are mentioned, include all. If none mentioned, return ["Unknown"].
- **Error handling**: If the paper does not discuss admission systems at all, return a single JSON object with all fields set to "Unknown" and notes explaining no relevant information was found.
- **Output valid JSON only**: No markdown, no commentary, just JSON.

### Example Output Structure:
[
    {
        "region": "Singapore",
        "iso3_country_code": "SGP",
        "education_level": "Secondary",
        "ccas_status": "Coordinated",
        "participating_institutions": "Public",
        "preference_list_length": 6,
        "priority_criteria": ["academic", "distance", "zone"],
        "assignment_mechanism": "Deferred Acceptance",
        "adoption_year": 1998,
        "reform_year": 2014,
        "notes": "Singapore's Integrated Result Slip system uses deferred acceptance..."
    },
    {
        "region": "Singapore",
        "iso3_country_code": "SGP",
        "education_level": "Primary",
        "ccas_status": "Uncoordinated",
        "participating_institutions": "Unknown",
        "preference_list_length": "Unknown",
        "priority_criteria": ["Unknown"],
        "assignment_mechanism": "Unknown",
        "adoption_year": "Unknown",
        "reform_year": "Unknown",
        "notes": "Primary education admissions are handled locally by schools without central coordination."
    }
]
"""
    return prompt_text