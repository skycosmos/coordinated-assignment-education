.headers on
.mode csv
.output ccas_city.csv
SELECT city, country, education_level, ccas_status, ccas_status_source, participating_institutions, participating_institutions_source, preference_list_length, preference_list_length_source, priority_criteria, priority_criteria_source, assignment_mechanism, assignment_mechanism_source, adoption_year, adoption_year_source, reform_year, reform_year_source, notes
FROM ccas_city;
.exit
