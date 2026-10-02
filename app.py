import streamlit as st
import streamlit.components.v1 as components # <-- ADD THIS LINE
import json
import pandas as pd
import re
import os

# Set page config to use full width
st.set_page_config(layout="wide", page_title="Election Dashboard", initial_sidebar_state="collapsed")
st.title("🇧🇩 Bangladesh 13th General Elections Dashboard")

# ==========================================
# 1. LOCAL FILE PATHS
# ==========================================
# Data Files
GEO_FILE = "data/300_Seats.geojson"
ELEC_FILE = "data/Election_Party_Dataset.csv"
REF_FILE = "data/Referendum_Dataset.csv"
STATS_FILE = "data/Constituency_Voting_Stats.csv"
SOCIO_FILE = "data/Socio_Economic_Data.csv"

# Image Files
EDA_IMG_1 = "images/socio factor.png"
EDA_IMG_2 = "images/internet and poverty.png"
EDA_IMG_3 = "images/correlation matrix.png"
HYP_IMG_1 = "images/hypothesisA.png"
HYP_IMG_2 = "images/HypothesisB.png"
HYP_IMG_3 = "images/HypothesisC.png"

# Validation Check to ensure you set up your folders right
if not os.path.exists(GEO_FILE) or not os.path.exists(ELEC_FILE):
    st.error("⚠️ Mandatory data files missing! Please ensure your 'data' folder contains the necessary files.")
    st.stop()

# ==========================================
# 2. HELPER FUNCTIONS & COLORS
# ==========================================
def get_division(seat_no):
    try:
        seat = int(float(seat_no))
        if 1 <= seat <= 33: return "Rangpur"
        elif 34 <= seat <= 72: return "Rajshahi"
        elif 73 <= seat <= 108: return "Khulna"
        elif 109 <= seat <= 129: return "Barishal"
        elif 130 <= seat <= 137: return "Dhaka"
        elif 138 <= seat <= 161: return "Mymensingh"
        elif 162 <= seat <= 223: return "Dhaka"
        elif 224 <= seat <= 243: return "Sylhet"
        elif 244 <= seat <= 300: return "Chattogram"
        else: return "Unknown"
    except:
        return "Unknown"

def clean_numeric(val):
    if pd.isna(val) or val is None: return 0.0
    if isinstance(val, (int, float)): return float(val)
    s = str(val).replace(',', '').replace('%', '').strip()
    try:
        return float(s)
    except:
        return 0.0

PARTY_COLORS = {
    "Bangladesh Awami League": "#006a4e", "Bangladesh Nationalist Party": "#00529b", 
    "Bangladesh Jamaat-e-Islami": "#004d00", "Independent Candidate": "#808080",        
    "Jatiya Party": "#e6e600", "Islami Andolan Bangladesh": "#8b4513",
    "Gono Odhikar Parishad": "#ff6600", "Bangladesh Khelafat Majlish": "#8e44ad"
}

EMOJI_COLORS = {
    "Bangladesh Awami League": "🟩", "Bangladesh Nationalist Party": "🟦", 
    "Bangladesh Jamaat-e-Islami": "🌲", "Independent Candidate": "⬜",        
    "Jatiya Party": "🟨", "Islami Andolan Bangladesh": "🟫",
    "Gono Odhikar Parishad": "🟧", "Bangladesh Khelafat Majlish": "🟪"
}

# ==========================================
# 3. DATA PROCESSING ENGINE
# ==========================================
@st.cache_data(show_spinner="Compiling Final Election Data...")
def compile_election_data():
    with open(GEO_FILE, 'r', encoding='utf-8') as f:
        geo_data = json.load(f)
        
    elec_df = pd.read_csv(ELEC_FILE, on_bad_lines='skip')
    ref_df = pd.read_csv(REF_FILE, on_bad_lines='skip') if os.path.exists(REF_FILE) else pd.DataFrame()
    stats_df = pd.read_csv(STATS_FILE, on_bad_lines='skip') if os.path.exists(STATS_FILE) else pd.DataFrame()
    socio_df = pd.read_csv(SOCIO_FILE, on_bad_lines='skip') if os.path.exists(SOCIO_FILE) else pd.DataFrame()
    
    seat_data = {}
    division_mapping = {}
    overall_party_wins = {}
    national_ref = {"yes": 0, "no": 0, "total": 0}
    
    if 'Seat_No' in elec_df.columns:
        vote_col = 'Candidate_Votes'
        if vote_col not in elec_df.columns:
            fallback = [c for c in elec_df.columns if 'vote' in c.lower() or 'total' in c.lower()]
            vote_col = fallback[0] if fallback else elec_df.columns[-1]

        grouped = elec_df.groupby('Seat_No')
        for seat_no, group in grouped:
            try:
                seat_num_int = int(float(seat_no))
            except:
                continue
                
            group['_sort_votes'] = group[vote_col].apply(clean_numeric)
            sorted_group = group.sort_values(by='_sort_votes', ascending=False)
            
            first_row = sorted_group.iloc[0]
            constituency_name = str(first_row.get('Constituency', f'Seat-{seat_num_int}'))
            division_name = get_division(seat_num_int)
            
            if division_name not in division_mapping:
                division_mapping[division_name] = []
            
            if not any(d['seat_no'] == seat_num_int for d in division_mapping[division_name]):
                division_mapping[division_name].append({"name": constituency_name, "seat_no": seat_num_int})
            
            candidates = []
            for _, row in sorted_group.iterrows():
                candidates.append({
                    "Name": str(row.get('Candidate_Name', 'Unknown')),
                    "Party": str(row.get('Party_Name', 'Unknown')),
                    "Votes": int(row['_sort_votes'])
                })
                
            winner = candidates[0]['Name'] if candidates else "Unknown"
            winner_party = candidates[0]['Party'] if candidates else "Unknown"
            overall_party_wins[winner_party] = overall_party_wins.get(winner_party, 0) + 1
            
            ref_info, voting_info, socio_info = None, None, None
            
            if not ref_df.empty and 'Constituency' in ref_df.columns:
                r_row = ref_df[ref_df['Constituency'].astype(str).str.contains(constituency_name, na=False, regex=False)]
                if not r_row.empty:
                    r = r_row.iloc[0]
                    ref_info = {
                        "yes_votes": int(clean_numeric(r.get('YES_Votes', 0))),
                        "no_votes": int(clean_numeric(r.get('NO_Votes', 0))),
                        "total": int(clean_numeric(r.get('Total_Ref_Votes', 0))),
                        "yes_pct": clean_numeric(r.get('YES_Pct', 0)),
                        "no_pct": clean_numeric(r.get('NO_Pct', 0)),
                    }
                    national_ref["yes"] += ref_info["yes_votes"]
                    national_ref["no"] += ref_info["no_votes"]
                    national_ref["total"] += ref_info["total"]

            if not stats_df.empty and 'Constituency' in stats_df.columns:
                s_row = stats_df[stats_df['Constituency'].astype(str).str.contains(constituency_name, na=False, regex=False)]
                if not s_row.empty:
                    s = s_row.iloc[0]
                    voting_info = {
                        "turnout": clean_numeric(s.get('Voter_Turnout_Pct', 0)),
                        "cast": int(clean_numeric(s.get('Total_Cast_Votes', 0))),
                        "valid": int(clean_numeric(s.get('Total_Valid_Votes', 0))),
                        "invalid": int(clean_numeric(s.get('Total_Invalid_Votes', 0))),
                    }

            if not socio_df.empty and 'Constituency' in socio_df.columns:
                so_row = socio_df[socio_df['Constituency'].astype(str).str.contains(constituency_name, na=False, regex=False)]
                if not so_row.empty:
                    so = so_row.iloc[0]
                    socio_info = {
                        "youth": clean_numeric(so.get('Youth_Electorate_Pct', 0)),
                        "poverty": clean_numeric(so.get('Extreme_Poverty_Pct', 0)),
                        "electricity": clean_numeric(so.get('Electricity_Pct', 0)),
                        "internet": clean_numeric(so.get('Internet_Pct', 0)),
                    }

            seat_data[seat_num_int] = {
                "seatName": constituency_name, "winner": winner, "party": winner_party,
                "candidates": candidates, "referendum": ref_info, "voting": voting_info, "socio": socio_info
            }
        
    for div in division_mapping:
        division_mapping[div] = sorted(division_mapping[div], key=lambda x: x['seat_no'])
        
    raw_dfs = {"elec": elec_df, "ref": ref_df, "stats": stats_df, "socio": socio_df}
    return geo_data, seat_data, division_mapping, raw_dfs, overall_party_wins, national_ref

try:
    geo_json_data, seat_results, division_map, raw_dfs, overall_party_wins, national_ref = compile_election_data()
except Exception as e:
    st.error(f"Data Compilation Error: {e}")
    st.stop()

# ==========================================
# 4. DASHBOARD UI
# ==========================================
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🗺️ 1. Interactive Map", "🔍 2. Constituency Results", "🏆 3. Overall Winners",
    "⚖️ 4. Total Referendum", "📁 5. Raw Data", "📊 6. EDA Analytics", "🧪 7. AI Hypotheses"
])

# ------------------------------------------
# TAB 1: INTERACTIVE MAP 
# ------------------------------------------
with tab1:
    st.markdown("### Party Color Legend")
    legend_text = " | ".join([f"{emoji} **{party}**" for party, emoji in EMOJI_COLORS.items()])
    st.markdown(f"> {legend_text}")
    st.caption("Click on any constituency on the map to view comprehensive details.")
    
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <style>
            body { margin: 0; background: #121212; font-family: Arial, sans-serif; overflow: hidden; }
            #map { height: 750px; width: 100%; transition: width 0.3s ease; border-radius: 8px;}
            .dark-tooltip { background: #1a1a1a !important; border: 1px solid #444 !important; color: white !important; padding: 10px; border-radius: 6px; }

            #details-panel {
                position: absolute; top: 0; right: -500px; width: 500px; height: 750px;
                background-color: #1e1e1e; color: #fff; z-index: 1000;
                box-shadow: -5px 0 15px rgba(0,0,0,0.5); overflow-y: auto;
                transition: right 0.3s ease; border-left: 1px solid #333;
            }
            
            .panel-header { background: #252525; padding: 20px; border-bottom: 1px solid #444; position: sticky; top: 0; z-index: 10; display: flex; justify-content: space-between; align-items: center; }
            .panel-header h2 { margin: 0; font-size: 22px; color: #4db8ff; }
            .close-btn { background: none; border: none; color: #aaa; font-size: 28px; cursor: pointer; padding: 0 10px; }
            .close-btn:hover { color: #fff; }

            .panel-content { padding: 20px; }
            .section-title { font-size: 14px; border-bottom: 2px solid #444; padding-bottom: 5px; margin-bottom: 15px; margin-top: 25px; color: #bbb; text-transform: uppercase; font-weight: bold;}
            
            .stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
            .stat-box { background: #2a2a2a; padding: 12px; border-radius: 6px; border: 1px solid #333; }
            .stat-label { font-size: 11px; color: #aaa; text-transform: uppercase; margin-bottom: 4px; }
            .stat-val { font-size: 18px; font-weight: bold; color: #fff; }
            
            table { width: 100%; border-collapse: collapse; margin-bottom: 30px; color: white; }
            th { text-align: left; padding: 8px 5px; color: #aaa; font-size: 12px; border-bottom: 1px solid #444; }
            td { padding: 10px 5px; border-bottom: 1px solid #2a2a2a; font-size: 14px; }
        </style>
    </head>
    <body>
        <div id="map"></div>
        <div id="details-panel">
            <div class="panel-header">
                <h2 id="panel-title">Seat Details</h2>
                <button class="close-btn" onclick="closePanel()">&times;</button>
            </div>
            <div class="panel-content" id="panel-body"></div>
        </div>

        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            const geoData = GEO_JSON_DATA;
            const results = SEAT_RESULTS;
            const partyColors = PARTY_COLORS_JSON;

            const map = L.map('map').setView([23.6850, 90.3563], 7);
            L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', { attribution: '© CARTO' }).addTo(map);

            const geoLayer = L.geoJSON(geoData, {
                style: (feature) => {
                    const res = results[feature.properties.Seat_No];
                    return { fillColor: res ? (partyColors[res.party] || "#808080") : "#333", fillOpacity: 0.8, color: "#111", weight: 1 };
                },
                onEachFeature: (feature, layer) => {
                    const seatNo = feature.properties.Seat_No;
                    const res = results[seatNo];
                    
                    if (res) {
                        layer.bindTooltip(`
                            <div style='font-size:16px'><b>Seat ${seatNo}</b></div>
                            <div style='color:#bbb'>${res.seatName}</div>
                            <div style='color:#4db8ff; font-weight:bold; margin-top:5px'>${res.winner}</div>
                            <div style='font-size:12px'>${res.party}</div>
                        `, { sticky: true, className: 'dark-tooltip' });
                        
                        layer.on('click', () => openPanel(seatNo, res));
                    }
                    
                    layer.on({
                        mouseover: (e) => { e.target.setStyle({ weight: 3, color: '#fff' }); e.target.bringToFront(); },
                        mouseout: (e) => { geoLayer.resetStyle(e.target); }
                    });
                }
            }).addTo(map);

            const panel = document.getElementById('details-panel');
            const mapDiv = document.getElementById('map');
            
            function openPanel(seatNo, data) {
                document.getElementById('panel-title').innerText = `${data.seatName} (Seat ${seatNo})`;
                
                let html = `<div class="section-title">🗳️ Winner</div>
                            <div class="stats-grid" style="grid-template-columns: 1fr;">
                                <div class="stat-box"><div class="stat-label">${data.party}</div><div class="stat-val" style="color: #4db8ff;">${data.winner}</div></div>
                            </div>`;
                
                if(data.candidates && data.candidates.length > 0) {
                    html += `<div class="section-title">👥 Candidates & Votes</div><table><tr><th>Candidate</th><th>Party</th><th>Votes</th></tr>`;
                    data.candidates.forEach(c => {
                        html += `<tr><td>${c.Name}</td><td>${c.Party}</td><td>${c.Votes.toLocaleString()}</td></tr>`;
                    });
                    html += `</table>`;
                }

                if(data.voting) {
                    html += `<div class="section-title">📊 Voting Statistics</div>
                             <div class="stats-grid">
                                <div class="stat-box"><div class="stat-label">Turnout</div><div class="stat-val">${data.voting.turnout}%</div></div>
                                <div class="stat-box"><div class="stat-label">Total Cast</div><div class="stat-val">${data.voting.cast.toLocaleString()}</div></div>
                                <div class="stat-box"><div class="stat-label">Valid Votes</div><div class="stat-val">${data.voting.valid.toLocaleString()}</div></div>
                                <div class="stat-box"><div class="stat-label">Invalid Votes</div><div class="stat-val">${data.voting.invalid.toLocaleString()}</div></div>
                             </div>`;
                }

                if(data.referendum) {
                    html += `<div class="section-title">⚖️ Referendum Results</div>
                             <div class="stats-grid">
                                <div class="stat-box"><div class="stat-label">YES Votes</div><div class="stat-val" style="color:#00e676;">${data.referendum.yes_pct}%</div></div>
                                <div class="stat-box"><div class="stat-label">NO Votes</div><div class="stat-val" style="color:#ff3d00;">${data.referendum.no_pct}%</div></div>
                             </div>`;
                }

                if(data.socio) {
                    html += `<div class="section-title">🏙️ Socio-Economic Indicators</div>
                             <div class="stats-grid">
                                <div class="stat-box"><div class="stat-label">Youth Electorate</div><div class="stat-val">${data.socio.youth}%</div></div>
                                <div class="stat-box"><div class="stat-label">Extreme Poverty</div><div class="stat-val">${data.socio.poverty}%</div></div>
                                <div class="stat-box"><div class="stat-label">Electricity Access</div><div class="stat-val">${data.socio.electricity}%</div></div>
                                <div class="stat-box"><div class="stat-label">Internet Access</div><div class="stat-val">${data.socio.internet}%</div></div>
                             </div>`;
                }

                document.getElementById('panel-body').innerHTML = html;
                panel.style.right = "0";
                mapDiv.style.width = "calc(100% - 500px)";
            }

            function closePanel() {
                panel.style.right = "-500px";
                mapDiv.style.width = "100%";
            }
        </script>
    </body>
    </html>
    """
    
    final_html = html_template.replace("GEO_JSON_DATA", json.dumps(geo_json_data))\
                              .replace("SEAT_RESULTS", json.dumps(seat_results))\
                              .replace("PARTY_COLORS_JSON", json.dumps(PARTY_COLORS))
    
    # # Using modern st.html instead of deprecated components.html
    # st.html(final_html)
    # Using components.html creates a secure iframe that allows Leaflet's JavaScript to execute
    components.html(final_html, height=750)

# ------------------------------------------
# TAB 2: CONSTITUENCY RESULTS
# ------------------------------------------
with tab2:
    st.header("🔍 Detailed Constituency Results")
    col1, col2 = st.columns(2)
    divisions = sorted(list(division_map.keys()))
    selected_div = col1.selectbox("1️⃣ Select Division", ["-- Select Division --"] + divisions)
    
    if selected_div == "-- Select Division --":
        col2.selectbox("2️⃣ Select Constituency", ["Please select a division first..."], disabled=True)
    else:
        constituencies = division_map[selected_div]
        const_options = ["-- Select Constituency --"] + [f"{c['name']} (Seat {c['seat_no']})" for c in constituencies]
        selected_const = col2.selectbox("2️⃣ Select Constituency", const_options)
        
        if selected_const != "-- Select Constituency --":
            seat_no_match = re.search(r'Seat (\d+)', selected_const)
            if seat_no_match:
                seat_num = int(seat_no_match.group(1))
                data = seat_results.get(seat_num)
                
                if data:
                    st.divider()
                    st.subheader(f"🏅 Winner: {data['winner']} | {data['party']}")
                    st.markdown("#### 👥 Candidates & Votes")
                    cand_df = pd.DataFrame(data['candidates'])
                    # Updated to width='stretch'
                    st.dataframe(cand_df.reset_index(drop=True).fillna("").astype(str), width='stretch', hide_index=True)

# ------------------------------------------
# TAB 3: OVERALL RESULTS
# ------------------------------------------
with tab3:
    st.header("🏆 Overall Election Results")
    st.write("Total parliamentary seats secured by each political party.")
    
    wins_df = pd.DataFrame(list(overall_party_wins.items()), columns=['Party', 'Seats Won'])
    wins_df = wins_df.sort_values(by='Seats Won', ascending=False).reset_index(drop=True)
    wins_df['Color'] = wins_df['Party'].apply(lambda p: PARTY_COLORS.get(p, "#808080"))
    wins_df['Party Name'] = wins_df['Party'].apply(lambda p: f"{EMOJI_COLORS.get(p, '⬛')} {p}")
    
    col_a, col_b = st.columns([1, 2])
    with col_a:
        display_df = wins_df[['Party Name', 'Seats Won']]
        st.dataframe(display_df.reset_index(drop=True).fillna("").astype(str), width='stretch', hide_index=True)
        
    with col_b:
        try:
            st.bar_chart(data=wins_df, x='Party', y='Seats Won', color='Color', width='stretch')
        except:
            st.bar_chart(wins_df.set_index('Party')['Seats Won'], width='stretch')

# ------------------------------------------
# TAB 4: TOTAL REFERENDUM
# ------------------------------------------
with tab4:
    st.header("⚖️ Total National Referendum Results")
    total_votes = national_ref['total']
    total_yes = national_ref['yes']
    total_no = national_ref['no']
    
    if total_votes > 0:
        yes_pct = round((total_yes / total_votes) * 100, 2)
        no_pct = round((total_no / total_votes) * 100, 2)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Referendum Votes", f"{total_votes:,}")
        col2.metric("Total YES Votes", f"{total_yes:,}", f"{yes_pct}%")
        col3.metric("Total NO Votes", f"{total_no:,}", f"-{no_pct}%")
        
        st.divider()
        st.subheader("National Referendum Split")
        
        ref_split_df = pd.DataFrame({"Vote": ["YES", "NO"], "Count": [total_yes, total_no]})
        st.bar_chart(ref_split_df.set_index("Vote"), width='stretch')
    else:
        st.info("Referendum data not available. Please ensure 'Referendum_Dataset.csv' is in your folder.")

# ------------------------------------------
# TAB 5: VIEW DATASETS
# ------------------------------------------
with tab5:
    st.header("📁 Raw Datasets Explorer")
    ds_choice = st.selectbox("Select Dataset to View", ["Election Candidates", "Referendum Data", "Voting Stats", "Socio-Economic"])
    
    if ds_choice == "Election Candidates" and not raw_dfs["elec"].empty: 
        st.dataframe(raw_dfs["elec"].reset_index(drop=True).fillna("").astype(str), width='stretch', hide_index=True)
    elif ds_choice == "Referendum Data" and not raw_dfs["ref"].empty: 
        st.dataframe(raw_dfs["ref"].reset_index(drop=True).fillna("").astype(str), width='stretch', hide_index=True)
    elif ds_choice == "Voting Stats" and not raw_dfs["stats"].empty: 
        st.dataframe(raw_dfs["stats"].reset_index(drop=True).fillna("").astype(str), width='stretch', hide_index=True)
    elif ds_choice == "Socio-Economic" and not raw_dfs["socio"].empty: 
        st.dataframe(raw_dfs["socio"].reset_index(drop=True).fillna("").astype(str), width='stretch', hide_index=True)
    else: 
        st.warning("This dataset was not found.")

# ------------------------------------------
# TAB 6: EDA ANALYTICS (FIXED IMAGE SIZING)
# ------------------------------------------
with tab6:
    st.header("📊 Exploratory Data Analysis (EDA)")
    st.write("Dynamic visual exploration generated from the PySpark data pipeline.")
    st.divider()
    
    eda_choice = st.radio("Select Analysis Module:", 
                          ["Correlation Analysis", "Feature Distributions", "Voting Scatter Plots"], 
                          horizontal=True)
    st.write("")
    
    if eda_choice == "Correlation Analysis":
        if os.path.exists(EDA_IMG_1): st.image(EDA_IMG_1, width=850)
        else: st.warning(f"Could not locate image: {EDA_IMG_1}")
            
    elif eda_choice == "Feature Distributions":
        if os.path.exists(EDA_IMG_2): st.image(EDA_IMG_2, width=850)
        else: st.warning(f"Could not locate image: {EDA_IMG_2}")
            
    elif eda_choice == "Voting Scatter Plots":
        if os.path.exists(EDA_IMG_3): st.image(EDA_IMG_3, width=850)
        else: st.warning(f"Could not locate image: {EDA_IMG_3}")

# ------------------------------------------
# TAB 7: HYPOTHESES (FIXED IMAGE SIZING)
# ------------------------------------------
with tab7:
    st.header("🧪 Advanced AI Hypotheses Testing")
    st.write("Results extracted from the PySpark MLlib Pipeline (`Controversial_Hypotheses.ipynb`)")
    st.divider()
    
    hyp_choice = st.selectbox("Select Hypothesis to Explore:", [
        "Hypothesis 1: The Pincer Movement (The Horseshoe Wealth Coalition)",
        "Hypothesis 2: The Digital Elitism Paradox",
        "Hypothesis 3: The Geopolitical Securitization Effect"
    ])
    
    st.write("") 
    
    if "Hypothesis 1" in hyp_choice:
        st.markdown("### 📌 Hypothesis 1: The Pincer Movement")
        st.write("**Theory:** The winning party secured a structural advantage by capturing both the highest wealth demographics (Urban Elite) and the lowest wealth demographics (Extreme Poverty), effectively squeezing out the middle-class vote.")
        st.write("* **Machine Learning Method:** K-Means Clustering & Demographic Stratification.")
        if os.path.exists(HYP_IMG_1): st.image(HYP_IMG_1, width=850)
        else: st.warning(f"Could not locate image: {HYP_IMG_1}")
            
    elif "Hypothesis 2" in hyp_choice:
        st.markdown("### 📌 Hypothesis 2: The Digital Elitism Paradox")
        st.write("**Theory:** High internet penetration actually correlates strongly with 'NO' votes on the national referendum, indicating a divergence between the highly-connected digital youth and the traditional rural electorate.")
        st.write("* **Machine Learning Method:** Random Forest Feature Importance.")
        if os.path.exists(HYP_IMG_2): st.image(HYP_IMG_2, width=850)
        else: st.warning(f"Could not locate image: {HYP_IMG_2}")
            
    elif "Hypothesis 3" in hyp_choice:
        st.markdown("### 📌 Hypothesis 3: The Geopolitical Securitization Effect")
        st.write("**Theory:** Constituencies located directly on the international border exhibited significantly different voting patterns (higher turnout, different party preference) compared to non-border districts, overriding standard poverty dynamics.")
        st.write("* **Machine Learning Method:** Geospatial Boolean Classification.")
        if os.path.exists(HYP_IMG_3): st.image(HYP_IMG_3, width=850)
        else: st.warning(f"Could not locate image: {HYP_IMG_3}")