// Scenario definitions
// Template for scenarios - teammate can add more following this structure
// datetime format: "YYYY-MM-DD HH:MM" (24-hour format, local Austin time)

export const SCENARIOS = {
  default: {
    id: "default",
    name: "Normal Operations",
    datetime: "2025-01-15 14:00",
    description: "Position your four ambulances to maximize coverage of high-risk zones. Red areas indicate higher predicted incident probability for the next hour.",
    hints: [
      "Downtown and entertainment districts typically see higher call volumes.",
      "Consider positioning units to minimize average response time across the city."
    ],
    difficulty: "normal",
    expectedIncidentRange: [15, 25],
    focusAreas: ["downtown", "university"],
  },
  sxsw: {
    id: "sxsw",
    name: "SXSW 2025",
    datetime: "2025-03-14 22:00",
    description: "South by Southwest is in full swing. Massive crowds concentrated downtown with multiple venues, outdoor stages, and late-night activities. Expect alcohol-related incidents and heat exhaustion.",
    hints: [
      "Convention Center and 6th Street corridor will see highest density.",
      "Rainey Street and East Austin venues are secondary hotspots.",
      "Peak hours: 10 PM - 2 AM for alcohol-related calls."
    ],
    difficulty: "hard",
    expectedIncidentRange: [40, 60],
    focusAreas: ["downtown", "6th-street", "rainey", "convention-center"],
  },
  acl: {
    id: "acl",
    name: "ACL Festival",
    datetime: "2025-10-04 15:00",
    description: "Austin City Limits Festival at Zilker Park. 75,000+ attendees daily with concentrated crowds, heat exposure, and limited vehicle access near the park.",
    hints: [
      "Zilker Park perimeter will have highest call volume.",
      "Barton Springs Road access is restricted - plan alternate routes.",
      "Heat-related emergencies peak mid-afternoon."
    ],
    difficulty: "hard",
    expectedIncidentRange: [35, 50],
    focusAreas: ["zilker", "barton-springs", "south-lamar"],
  },
  f1: {
    id: "f1",
    name: "F1 US Grand Prix",
    datetime: "2025-10-19 13:00",
    description: "Circuit of the Americas hosts 120,000+ race fans. Traffic congestion severe on east side. High-speed incidents possible near track, crowd crush risks at gates.",
    hints: [
      "COTA area will dominate call volume during race hours.",
      "Downtown hotels see spillover evening incidents.",
      "Airport corridor also experiences elevated activity."
    ],
    difficulty: "hard",
    expectedIncidentRange: [30, 45],
    focusAreas: ["cota", "airport", "downtown"],
  },
  july4: {
    id: "july4",
    name: "Fourth of July",
    datetime: "2025-07-04 21:00",
    description: "Independence Day celebrations across Austin. Multiple firework viewing locations, lakeside gatherings, and backyard parties citywide. Burns, trauma, and alcohol incidents elevated.",
    hints: [
      "Auditorium Shores and Lady Bird Lake are primary gathering spots.",
      "Residential areas see increased firework-related injuries.",
      "Call volume spikes dramatically after 9 PM."
    ],
    difficulty: "medium",
    expectedIncidentRange: [25, 40],
    focusAreas: ["lady-bird-lake", "auditorium-shores", "residential"],
  },
  halloween: {
    id: "halloween",
    name: "Halloween Weekend",
    datetime: "2025-11-01 23:00",
    description: "6th Street transforms into Austin's largest costume party. Extremely dense pedestrian crowds, alcohol-heavy environment, and limited vehicle access downtown.",
    hints: [
      "6th Street between Congress and I-35 is the epicenter.",
      "Expect costume-related visibility issues for patients.",
      "Peak calls between 11 PM and 3 AM."
    ],
    difficulty: "medium",
    expectedIncidentRange: [30, 45],
    focusAreas: ["6th-street", "downtown", "west-campus"],
  },
  nye: {
    id: "nye",
    name: "New Year's Eve",
    datetime: "2025-12-31 23:00",
    description: "Multiple countdown events across Austin. Auditorium Shores main event, plus 6th Street, Rainey, and Domain gatherings. DUI incidents spike after midnight.",
    hints: [
      "Position for rapid response to downtown and south-central.",
      "Post-midnight DUI incidents spread across highway corridors.",
      "Cold weather increases slip/fall calls."
    ],
    difficulty: "medium",
    expectedIncidentRange: [25, 35],
    focusAreas: ["downtown", "auditorium-shores", "highways"],
  },
  ut_game: {
    id: "ut_game",
    name: "UT Football Game",
    datetime: "2025-09-06 18:00",
    description: "Longhorns home game at DKR Stadium. 100,000+ fans converge on campus. Tailgating starts early, crowd surge at kickoff and end of game.",
    hints: [
      "Campus and stadium perimeter are primary hotspots.",
      "MLK Blvd and I-35 see major congestion.",
      "Alcohol-related calls spike pre-game and post-game."
    ],
    difficulty: "medium",
    expectedIncidentRange: [20, 35],
    focusAreas: ["ut-campus", "stadium", "west-campus"],
  },
};

export function getScenario(id) {
  return SCENARIOS[id] || SCENARIOS.default;
}

export function getAllScenarioIds() {
  return Object.keys(SCENARIOS);
}
