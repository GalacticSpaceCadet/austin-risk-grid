## **Prizes: $1,000 Cash**

**The Problem:** Right now, Austin’s emergency response is completely reactive. A tow truck sits at a depot until a 911 call comes in, and by the time they get to I-35, the traffic is already backed up for miles. We can assume that crashes aren't random; they follow patterns based on the time of day, rain, and heat. It would be incredibly valuable if we could "see the future" of the grid and position safety assets near high-risk corridors *before* the incidents actually happen.

**The Goal:** Build a system that helps derive actionable insights from traffic incident reports (using weather data is optional).

### Dataset

[**Austin Real-Time Traffic Incident Reports](https://data.austintexas.gov/Transportation-and-Mobility/Real-Time-Traffic-Incident-Reports/dx9v-zd7x) (Live & Historical: Crashes, Stalls, Hazards)**

*Optional Enrichment:* [NOAA Weather API](https://www.weather.gov/documentation/services-web-api)

<aside>
<img src="/icons/light-bulb_orange.svg" alt="/icons/light-bulb_orange.svg" width="40px" />

### About

This dataset contains traffic incident information from the Austin-Travis County traffic reports collected from the various Public Safety agencies through a data feed from the Combined Transportation, Emergency, and Communications Center (CTECC).

For further context, see:

Active Incidents: Map and Context -

https://data.austintexas.gov/stories/s/Austin-Travis-County-Traffic-Report-Page/9qfg-4swh/

Data Trends and Analysis -

https://data.austintexas.gov/stories/s/48n7-m3me

The dataset is updated every 5 minutes with the latest snapshot of active traffic incidents.

</aside>

**Suggested Directions (Inspiration Only):**

- ***Predictive Alerting:* Forecast high-risk "Hotspots" for the next hour to stage tow trucks early.**
- ***Contextual Intelligence:* Correlate weather events (Rain/Ice) with crash types to change deployment strategies.**
- ***Digital Twin:* Simulate how traffic would flow if you proactively closed a dangerous ramp.**

**Examples:**

- **Hotspot Agent Watcher:** Build a system that learns the "Rhythm of the City" to predict hotspots based on time/day and visualizes where units should be stationed. An agent that divides Austin into a grid and assigns a "Risk Score" to each sector for every hour of the day.
- **Weather Watcher:** Build a system that understands *context*. It correlates traffic incidents with historical weather data to predict how rain, heat, or freezing conditions radically change safety risks. An agent that ingests the *current* weather forecast and modifies the standard deployment plan.

<aside>
<img src="/icons/code_orange.svg" alt="/icons/code_orange.svg" width="40px" />

### API Access & Usage

1. Make account here and create App Token in [Developer Settings](https://evergreen.data.socrata.com/profile/edit/developer_settings): https://evergreen.data.socrata.com/ 
2. [**API Documentation Here**](https://dev.socrata.com/foundry/data.austintexas.gov/dx9v-zd7x)
3. [**Read about using queries with SODA 3**](https://dev.socrata.com/docs/queries/)
</aside>

---
### Build Challenges

### **Context**

Teams will choose a build challenge and come up with a solution that meets the minimum required outcomes. What you build is more open-ended because we won’t be asking for a specific product to be built from the dataset. The goal is to come up with a solution that you think best meets the needs of the outcomes we want to see.

[Traffic Incident Insights](https://www.notion.so/Traffic-Incident-Insights-2c31e636288e81acbefce20e9fef7b98?pvs=21)

[**Factory Safety & Efficiency**](https://www.notion.so/Factory-Safety-Efficiency-2c31e636288e80d1ab86d335d9502c96?pvs=21)

[**Urban Growth & Infrastructure Intelligence**](https://www.notion.so/Urban-Growth-Infrastructure-Intelligence-2c31e636288e807d9483c64b38f6e8b0?pvs=21)

### *Partner Challenges*
---
### Judging Criteria

**Philosophy**

We are judging **Systems Engineering**. A winning project isn't just a slide deck or a simple API wrapper; it is a functioning system that ingests raw data, processes it locally using the DGX Spark, and produces a valuable result.

**The Scoring Breakdown (100 Points Total)**

### **1. Technical Execution & Completeness (30 Points)**

*Did they actually build a working, complex system?*

- **15 pts - Completeness:** Does the system successfully complete the full data workflow without crashing?
- **15 pts - Technical Depth:** Is there significant engineering "under the hood"? Did they build a complex pipeline (e.g., Simulation, RAG, Fine-Tuning, or Custom Logic) rather than just a simple static dashboard or basic API wrapper?

### **2. NVIDIA Ecosystem & Spark Utility (30 Points)**

*Did they leverage the unique hardware and software provided?*

- **15 pts - The Stack:** Did they use at least one major NVIDIA library/tool? (e.g., **NIMs**, **RAPIDS**, **cuOpt**, **Modulus**, **NeMo Models**). *Note: Merely calling GPT-4 via API gets 0 points here.*
- **15 pts - The "Spark Story":** Can they articulate **why** this runs better on a DGX Spark?
    - *Examples:* "We used the 128GB Unified Memory to hold the video buffer and the LLM context simultaneously" or "We ran inference locally to ensure privacy/latency."

### **3. Value & Impact (20 Points)**

*Is the solution actually useful?*

- **10 pts - Insight Quality:** Is the insight non-obvious and valuable? (e.g., "Traffic jams happen at 5 PM" is obvious. "Rain causes specific stalls on this specific ramp" is valuable).
- **10 pts - Usability:** Could a real Fire Chief, City Planner, or Factory Foreman actually use this tool to make a decision tomorrow?

### **4. The "Frontier" Factor (20 Points)**

*Did they push the boundaries?*

- **10 pts - Creativity:** Did they combine data or models in a novel way? (e.g., Using vision models to "read" traffic maps).
- **10 pts - Performance:** Did they optimize the system for speed or scale? (e.g., "We optimized the simulation to run at 50x real-time speed").