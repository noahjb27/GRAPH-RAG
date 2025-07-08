-- 1. TEMPORAL COVERAGE ANALYSIS
-- Check what years are actually available
MATCH (y:Year)
RETURN y.year as available_years
ORDER BY y.year;

-- Check station coverage by year
MATCH (s:Station)-[:IN_YEAR]->(y:Year)
RETURN y.year as year,      
       count(s) as station_count,
       count(DISTINCT s.type) as transport_types,
       collect(DISTINCT s.type) as types_available
ORDER BY y.year;

-- Check line coverage by year  
MATCH (l:Line)-[:IN_YEAR]->(y:Year)
WHERE l.frequency IS NOT NULL
RETURN y.year as year,
       count(l) as line_count,
       avg(l.frequency) as avg_frequency,
       collect(DISTINCT l.type) as line_types
ORDER BY y.year;

-- 2. ADMINISTRATIVE GEOGRAPHY CHECK
-- Available Bezirke (districts) with temporal data
MATCH (hb:HistoricalBezirk)-[:IN_YEAR]->(y:Year)
RETURN hb.name as bezirk_name, 
       collect(DISTINCT y.year) as active_years,
       count(y) as year_count
ORDER BY hb.name;

-- Available Ortsteile (neighborhoods) with temporal data
MATCH (ho:HistoricalOrtsteil)-[:IN_YEAR]->(y:Year)
RETURN ho.name as ortsteil_name,
       collect(DISTINCT y.year) as active_years,
       count(y) as year_count
ORDER BY ho.name
LIMIT 20;

-- Check which Ortsteile have the most station coverage
MATCH (s:Station)-[:LOCATED_IN]->(ho:HistoricalOrtsteil)
MATCH (ho)-[:IN_YEAR]->(y:Year)
RETURN ho.name as ortsteil_name,
       count(DISTINCT s) as station_count,
       collect(DISTINCT y.year) as years_with_data,
       collect(DISTINCT s.type) as transport_types
ORDER BY station_count DESC
LIMIT 15;

-- 3. SPECIFIC ENTITY VERIFICATION
-- Check for key stations mentioned in questions
MATCH (s:Station)
WHERE s.name CONTAINS 'Alexanderplatz' 
   OR s.name CONTAINS 'Ostbahnhof'
   OR s.name CONTAINS 'Potsdamer Platz' 
   OR s.name CONTAINS 'Zoo'
   OR s.name CONTAINS 'Bahnhof Zoo'
MATCH (s)-[:IN_YEAR]->(y:Year)
RETURN s.name as station_name, 
       s.type as transport_type,
       s.east_west as political_side,
       collect(y.year) as active_years
ORDER BY s.name;

-- Check for specific line numbers
MATCH (l:Line)
WHERE l.name IN ['1', '5', '6', 'U1', 'U5', 'U6', 'S1', 'S5', 'S6']
MATCH (l)-[:IN_YEAR]->(y:Year)
RETURN l.name as line_name,
       l.type as transport_type, 
       l.east_west as political_side,
       l.frequency as frequency,
       l.capacity as capacity,
       collect(y.year) as active_years
ORDER BY l.name;

-- 4. EAST-WEST DISTRIBUTION ANALYSIS
-- Station distribution by political side and year
MATCH (s:Station)-[:IN_YEAR]->(y:Year)
WHERE s.east_west IS NOT NULL
RETURN y.year as year,
       s.east_west as political_side,
       count(s) as station_count,
       collect(DISTINCT s.type) as transport_types
ORDER BY y.year, s.east_west;

-- Line distribution by political side
MATCH (l:Line)-[:IN_YEAR]->(y:Year)
WHERE l.east_west IS NOT NULL AND l.frequency IS NOT NULL
RETURN y.year as year,
       l.east_west as political_side,
       l.type as transport_type,
       count(l) as line_count,
       avg(l.frequency) as avg_frequency,
       avg(l.capacity) as avg_capacity
ORDER BY y.year, l.east_west, l.type;

-- 5. CAPACITY AND FREQUENCY DATA COMPLETENESS
-- Check data completeness for different transport types
MATCH (l:Line)-[:IN_YEAR]->(y:Year)
RETURN l.type as transport_type,
       count(l) as total_lines,
       count(CASE WHEN l.frequency IS NOT NULL THEN 1 END) as lines_with_frequency,
       count(CASE WHEN l.capacity IS NOT NULL THEN 1 END) as lines_with_capacity,
       avg(l.frequency) as avg_frequency,
       avg(l.capacity) as avg_capacity,
       min(y.year) as earliest_year,
       max(y.year) as latest_year
ORDER BY total_lines DESC;

-- 6. NETWORK CONNECTIVITY VERIFICATION
-- Check connection data availability
MATCH (s1:Station)-[c:CONNECTS_TO]->(s2:Station)
WHERE c.hourly_capacity IS NOT NULL
MATCH (s1)-[:IN_YEAR]->(y:Year)
RETURN y.year as year,
       count(c) as connections_with_capacity,
       avg(c.hourly_capacity) as avg_hourly_capacity,
       avg(c.distance_meters) as avg_distance_meters,
       collect(DISTINCT c.transport_type) as connection_types
ORDER BY y.year;

-- Check line-station serving relationships
MATCH (l:Line)-[s:SERVES]->(st:Station)
WHERE s.stop_order IS NOT NULL
MATCH (l)-[:IN_YEAR]->(y:Year)
RETURN y.year as year,
       l.type as transport_type,
       count(*) as serves_relationships,
       count(DISTINCT l.name) as unique_lines,
       count(DISTINCT st.name) as unique_stations
ORDER BY y.year, l.type;

-- 7. ADMINISTRATIVE HIERARCHY CHECK
-- Check Ortsteil-Bezirk relationships
MATCH (ho:HistoricalOrtsteil)-[:PART_OF]->(hb:HistoricalBezirk)
MATCH (ho)-[:IN_YEAR]->(y1:Year)
MATCH (hb)-[:IN_YEAR]->(y2:Year)
WHERE y1.year = y2.year
RETURN hb.name as bezirk,
       collect(DISTINCT ho.name) as ortsteile,
       count(ho) as ortsteil_count,
       collect(DISTINCT y1.year) as shared_years
ORDER BY bezirk;

-- 8. SAMPLE CROSS-BORDER ANALYSIS (Pre-1961)
-- Lines that potentially crossed East-West before 1961
MATCH (l:Line)-[:SERVES]->(s1:Station {east_west: 'east'})
MATCH (l)-[:SERVES]->(s2:Station {east_west: 'west'})  
MATCH (l)-[:IN_YEAR]->(y:Year)
WHERE y.year < 1961
RETURN y.year as year,
       l.name as line_name,
       l.type as transport_type,
       count(DISTINCT s1) as east_stations,
       count(DISTINCT s2) as west_stations
ORDER BY y.year, l.name;

-- 9. GEOGRAPHIC COVERAGE SAMPLE
-- Sample of stations with geographic and administrative data
MATCH (s:Station)-[:LOCATED_IN]->(ho:HistoricalOrtsteil)
MATCH (ho)-[:PART_OF]->(hb:HistoricalBezirk)
MATCH (s)-[:IN_YEAR]->(y:Year)
MATCH (ho)-[:IN_YEAR]->(y)
MATCH (hb)-[:IN_YEAR]->(y)
WHERE s.latitude IS NOT NULL AND s.longitude IS NOT NULL
RETURN s.name as station_name,
       s.type as transport_type,
       s.east_west as political_side,
       ho.name as ortsteil,
       hb.name as bezirk,
       y.year as year,
       s.latitude as lat,
       s.longitude as lon
ORDER BY y.year, hb.name, ho.name
LIMIT 20;

-- 10. TRANSPORT TYPE EVOLUTION
-- How transport types changed over time
MATCH (s:Station)-[:IN_YEAR]->(y:Year)
RETURN y.year as year,
       s.type as transport_type,
       s.east_west as political_side,
       count(s) as station_count
ORDER BY y.year, s.type, s.east_west;
