# Berlin Transit Network Database Documentation

## Database Overview

This Neo4j database contains a comprehensive historical model of Berlin's public transportation network and administrative boundaries from **1946-1989**, covering the crucial period from post-WWII reconstruction through the fall of the Berlin Wall. The database employs a sophisticated temporal design pattern that tracks both canonical entities and their historical snapshots across time.

**Key Characteristics:**

- **Temporal Scope**: 1946-1989 (44-year span)
- **Geographic Focus**: Berlin transit system and administrative divisions
- **Data Model**: Core entities + Historical snapshots pattern
- **Political Context**: Captures East/West Berlin division
- **Entity Count**: 23,157 total nodes, 77,022 relationships

## Data Model Architecture

### Core Design Pattern: Canonical + Temporal Snapshots

The database employs a **dual-layer temporal model**:

1. **Core Entities** (`Core*` nodes): Represent canonical, unified entities that persist across time
2. **Historical Snapshots** (`Historical*` nodes + temporal `Station`/`Line`): Capture specific states at particular years
3. **Temporal Linking**: `HAS_SNAPSHOT` relationships connect core entities to their historical manifestations

This design allows querying both:

- **Diachronic analysis**: How entities changed over time
- **Synchronic analysis**: Complete network state at any given year

### Political Geography Integration

The **East/West division** is systematically captured:

- `east_west` property values: `"east"`, `"west"`, `"unified"`
- Reflects the political reality of divided Berlin (1949-1989)
- Enables analysis of infrastructure development patterns across sectors

## Node Types & Properties

### Transit Infrastructure

#### **Station** (15,709 nodes)

Raw historical station data from archival sources

**Core Properties:**

- `stop_id` (string): Unique identifier from historical timetables
- `name` (string): Station name as recorded historically  
- `type` (string): Transport mode (omnibus, tram, s-bahn, u-bahn, ferry, autobus)
- `east_west` (string): Political sector (east/west/unified)
- `latitude`, `longitude` (float): Geographic coordinates
- `source` (string): Data provenance (primarily "Fahrplanbuch")

**Data Quality**: 100% completeness across all properties

#### **CoreStation** (5,503 nodes)

Canonical station entities resolved across time periods

**Enhanced Properties:**

- `core_id` (string): Unified identifier across temporal variations
- `activity_period` (JSON): Temporal activity metadata including observation years
- `source_confidence` (float): Data quality assessment (0.0-1.0)
- `in_lines` (array): Connected transit lines
- `created_date`, `updated_date` (datetime): System metadata

**Temporal Resolution Logic:**

- Consolidates stations with identical locations/names across years
- Tracks confidence levels for entity resolution decisions
- Maintains provenance chains through `source` attribution

#### **Line** (1,359 nodes)

Historical transit line instances

**Operational Properties:**

- `line_id` (string): Historical line identifier
- `name` (string): Line designation (numbers, letters, route names)
- `type` (string): Service type (omnibus, tram, s-bahn, u-bahn, ferry, autobus, oberleitungsbus)
- `frequency` (float): Service frequency in minutes
- `capacity` (integer): Vehicle capacity (passengers) - **Complete dataset with standardized values**
- `length_km` (float): Route length in kilometers
- `length_time` (float): Journey time (0-9 scale)
- `profile` (string): Additional route characteristics

#### **CoreLine** (588 nodes)

Canonical line entities spanning multiple time periods

**Unified Properties:**

- `core_line_id` (string): Canonical identifier
- `activity_period` (JSON): Complete temporal activity profile
- `source_confidence` (float): Resolution confidence metric

### Administrative Geography

#### **CoreOrtsteil** (98 nodes)

Canonical neighborhood/district entities

**Spatial Properties:**

- `centroid_lat`, `centroid_lon` (float): Geographic center
- `bbox_*` (float): Bounding rectangle coordinates  
- `area_km2` (float): Area in square kilometers
- `geometry_file` (string): Associated spatial data file
- `geometry_type` (string): Spatial data format

**Administrative Properties:**

- `current_bezirk` (string): Parent district assignment
- `creation_type` (string): How the area was established
- `research_status` (string): Data verification status
- `wikidata_id` (string): External reference linking
- `dissolved_date` (date): End of administrative existence (if applicable)

#### **HistoricalOrtsteil** (1,068 nodes)

Temporal snapshots of neighborhoods with demographic data

**Demographic Properties:**

- `population` (integer): Resident count for snapshot year
- `population_density` (float): People per square kilometer  
- `area_km2` (float): Administrative area
- `data_source` (string): Statistical data provenance
- `has_statistical_data` (boolean): Data availability flag

#### **CoreBezirk** (23 nodes) / **HistoricalBezirk** (288 nodes)

District-level administrative entities and their temporal snapshots

**Political Properties:**

- `settlement_area_ha` (float): Developed area in hectares
- `start_date` (date): Administrative establishment date (1946-1986)
- `creation_reason` (string): Historical context for creation
- `created_from` (string): Predecessor administrative units

### Temporal Framework

#### **Year** (14 connected nodes)

Temporal anchor points for historical snapshots

**Active Years**: 1946, 1951, 1956, 1960, 1961, 1964, 1965, 1967, 1971, 1980, 1982, 1984, 1985, 1989

**Notable Patterns:**

- Concentrated around major political transitions
- 1946: Post-war administrative reorganization  
- 1989: Fall of Berlin Wall
- Missing years represent data gaps in historical sources

## Relationship Types & Semantics

### **Transit Network Connectivity**

#### **SERVES** (31,456 relationships)

`(Line)-[:SERVES]->(Station)`

- **Purpose**: Defines transit line routing through stations
- **Properties**: `stop_order` (integer) - sequence along route
- **Network Role**: Primary connectivity backbone

#### **CONNECTS_TO** (28,698 relationships)

`(Station)-[:CONNECTS_TO]->(Station)`

- **Purpose**: Direct connections between stations
- **Properties**: Rich operational metadata
  - `line_ids`, `line_names` (arrays): Connecting services
  - `transport_type` (string): Connection mode
  - `distance_meters` (float): Physical distance
  - `capacities`, `frequencies` (arrays): Service characteristics
  - `hourly_capacity`, `hourly_services` (integer): Aggregate capacity metrics

#### **SERVES_CORE** (17,890 relationships)

`(CoreLine)-[:SERVES_CORE]->(CoreStation)`

- **Purpose**: Canonical routing relationships across time
- **Properties**:
  - `overlapping_snapshots` (array): Shared temporal periods
  - `connection_strength` (float): Relationship confidence
- **Temporal Logic**: Aggregates multiple historical SERVES relationships

### **Temporal Linking**

#### **HAS_SNAPSHOT** (38,576 relationships)

`(Core*)-[:HAS_SNAPSHOT]->(Historical*/Station/Line)`

- **Purpose**: Links canonical entities to temporal manifestations
- **Properties**: `snapshot_year` (integer), `created_date` (datetime)
- **Patterns**:
  - `CoreStation` → `Station`: 15,214 relationships
  - `CoreLine` → `Line`: 2,718 relationships  
  - `CoreBezirk` → `HistoricalBezirk`: 288 relationships
  - `CoreOrtsteil` → `HistoricalOrtsteil`: 1,068 relationships

#### **IN_YEAR** (36,848 relationships)

`(Entity)-[:IN_YEAR]->(Year)`

- **Purpose**: Temporal grounding for historical entities
- **Distribution**:
  - Stations: 15,709 relationships
  - Lines: 1,359 relationships  
  - HistoricalOrtsteil: 1,068 relationships
  - HistoricalBezirk: 288 relationships

### **Geographic Hierarchy**

#### **LOCATED_IN** (25,930 relationships)

`(Station)-[:LOCATED_IN]->(HistoricalOrtsteil)`

- **Purpose**: Spatial containment of transit infrastructure
- **Properties**:
  - `assignment_method` (string): How location was determined
  - `geometry_coordinate_system` (string): Spatial reference system
  - `distance_to_centroid_km` (float): Distance from area center
- **Coverage**: 82.6% of stations have location assignments

#### **PART_OF** (1,630 relationships)

`(HistoricalOrtsteil)-[:PART_OF]->(HistoricalBezirk)`

- **Purpose**: Administrative hierarchy (neighborhoods → districts)
- **Properties**:
  - `transfer_notes` (string): Administrative change details
  - `partial_transfer` (boolean): Incomplete boundary changes
  - `assignment_start_date`, `assignment_end_date` (date): Validity period

## Temporal Coverage & Data Patterns

### **Historical Span Analysis**

**Data Creation Timeline:**

- **Core Entities**: Created 2025-06-10 (transit) / 2025-06-23 (administrative)
- **Historical Range**: 1946-1989 (post-WWII to German reunification)
- **Administrative Dates**: 1946-1986 (district establishment period)

**Temporal Distribution:**

- **1946**: Foundation year (immediate post-war)
- **1950s-1960s**: Reconstruction and expansion period
- **1970s-1980s**: System maturation and modernization
- **1989**: Terminal year (political transition)

### **Geographic Coverage**

**Coordinate Bounds:**

- **Latitude Range**: ~52.4° - 52.6° N (covers Greater Berlin area)
- **Longitude Range**: ~13.1° - 13.7° E (spans East-West divide)

**Spatial Data Availability:**

- **Stations**: 100% geocoded (15,709 with coordinates)
- **CoreOrtsteil**: 99% with full spatial metadata (97/98 nodes)
- **Demographics**: 19% coverage for HistoricalBezirk, 19% for HistoricalOrtsteil

## Transit Network Characteristics

### **Service Type Distribution**

Complete transport mode coverage with standardized capacity values:

- **Omnibus**: Traditional bus services (14 lines, 80 passengers)
- **Autobus**: Specialized bus services (690 lines, 100 passengers)
- **Oberleitungsbus**: Electric trolleybus services (14 lines, 80 passengers)
- **Tram**: Electric streetcar network (382 lines, 195 passengers)
- **S-Bahn**: Suburban rail services (155 lines, 1,100 passengers)
- **U-Bahn**: Underground/metro services (89 lines, 750-1,000 passengers)
- **Ferry**: Water transport connections (15 lines, 50-300 passengers)

**Transport Type Evolution Notes:**

- **Oberleitungsbus** represents Berlin's extensive trolleybus network (lines O30, O37, O40, O41)
- **East/West variations** capture different operational periods and political sectors
- **Capacity standardization** based on historical vehicle specifications for the 1946-1989 period

### **Network Connectivity Metrics**

- **Average Station Connections**: ~1.8 direct connections per station
- **Line-Station Density**: ~2.3 stations per line on average
- **Core Consolidation Ratio**:
  - Stations: 35% consolidation (15,709 → 5,503)
  - Lines: 43% consolidation (1,359 → 588)

### **Capacity Characteristics**

**Complete Capacity Dataset:**

- **Rail Services**: S-Bahn (1,100), U-Bahn (750-1,000), Tram (195)
- **Bus Services**: Autobus (100), Omnibus (80), Oberleitungsbus (80)
- **Water Transport**: Ferry (50-300, with larger vessels at 300)

**Service Frequency**: 12-120 minute intervals across all modes
**Journey Times**: 0-9 scale (standardized relative measure)

**Capacity Standards Applied:**

- Based on historical vehicle specifications for Berlin 1946-1989
- Reflects typical passenger loads for each transport mode
- Accounts for vehicle size variations (buses vs. rail cars vs. ferries)

## Data Quality Assessment

### **Completeness Metrics**

- **Station Properties**: 100% completeness across all core attributes
- **Line Capacity Data**: 100% completeness with standardized historical values
- **Temporal Linking**: Comprehensive coverage with 36,848 IN_YEAR relationships
- **Geographic Assignment**: 82.6% spatial coverage (25,930/31,456 possible locations)
- **Transport Type Classification**: Complete taxonomy including specialized services (oberleitungsbus)

### **Data Provenance**

- **Primary Source**: "Fahrplanbuch" (historical timetables)
- **Core Resolution**: "core_entity_resolver" (algorithmic unification)
- **Confidence Scoring**: 0.9-1.0 range for core entities
- **Capacity Standardization**: Historical vehicle specifications applied systematically

### **Known Limitations**

- **Demographic Coverage**: Only 19% of administrative areas have population data
- **Temporal Gaps**: Missing years between documented snapshots
- **Ferry Capacity Variation**: Range reflects different vessel sizes (50-300 passengers)

## Research Applications

### **Digital Humanities Applications**

**Urban History Research:**

- Infrastructure development patterns across political divide
- Post-war reconstruction timeline analysis
- East-West connectivity evolution

**Transportation Geography:**

- Network topology changes over time
- Service frequency and capacity trends
- Modal shift analysis (tram → bus transitions)

**Political Geography:**

- Administrative boundary evolution
- Cross-sector connectivity patterns
- Demographic change tracking

### **Analytical Capabilities**

**Temporal Queries:**

- Network state reconstruction for any year 1946-1989
- Infrastructure development timelines
- Service evolution tracking

**Spatial Analysis:**

- Accessibility pattern analysis
- Administrative boundary impact assessment
- Cross-sector connectivity measurement

**Network Analysis:**

- Centrality measure calculation across time
- Connectivity resilience assessment
- Service coverage optimization

## Technical Implementation Notes

### **Data Import Strategy**

- **Batch Processing**: Coordinated timestamps suggest systematic import
- **Entity Resolution**: Sophisticated matching algorithms for temporal consolidation
- **Quality Control**: Confidence scoring and source attribution throughout

### **Schema Evolution Evidence**

The database shows evidence of iterative development:

- **Removed Elements**: Cleaned empty node types (District, Ortsteil, PostalCode) and unused relationships (ASSIGNED_TO)
- **Property Versioning**: Multiple property variations suggest schema refinement
- **Constraint Management**: Comprehensive uniqueness constraints across entity types

### **Performance Considerations**

- **Indexing Strategy**: Comprehensive indexes on key identifiers and temporal properties
- **Spatial Indexing**: Multi-dimensional indexes for coordinate-based queries
- **Temporal Indexes**: Optimized for year-based filtering and range queries

## Conclusion

This database represents a sophisticated digital humanities resource that successfully models the complex temporal and spatial evolution of Berlin's transit infrastructure during a critical historical period. The dual-layer design (canonical + temporal) enables both detailed historical analysis and longitudinal trend identification, making it valuable for urban history, transportation geography, and political science research.

**Key Strengths:**

- Comprehensive temporal coverage (1946-1989)
- Complete capacity dataset with historically-grounded values
- Sophisticated entity resolution across time
- Detailed transport type classification (including oberleitungsbus)
- Rich spatial and administrative context
- Clear provenance and confidence tracking

**Data Enhancement Completed:**

- **Capacity Standardization**: Applied historical vehicle specifications across all transport modes
- **Transport Type Refinement**: Distinguished oberleitungsbus (trolleybus) from traditional omnibus services
- **Schema Optimization**: Removed unused node types and isolated temporal entities

**Research Value:**

- Enables quantitative analysis of post-war urban development
- Supports comparative East-West infrastructure studies  
- Provides foundation for network analysis across political transitions
- Offers case study for temporal graph database design in digital humanities

---

*Database documentation generated from Neo4j schema analysis and data profiling*
*Analysis Date: July 2025*
*Database Version: Enhanced with complete capacity data and refined transport type classification*
