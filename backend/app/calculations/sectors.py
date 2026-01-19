"""Bangladesh Stock Market Sector Classification and Analysis.

Provides sector-specific context for DSE stocks based on Bangladesh's
geopolitical and economic realities.
"""
from dataclasses import dataclass
from typing import Optional, List, Dict
from enum import Enum


class Sector(Enum):
    """DSE Sector Classifications."""
    PHARMACEUTICALS = "Pharmaceuticals"
    BANKING = "Banking"
    NBFI = "NBFI"  # Non-Bank Financial Institutions
    CEMENT = "Cement"
    FMCG = "FMCG"  # Fast Moving Consumer Goods
    TEXTILES_RMG = "Textiles & RMG"
    POWER_ENERGY = "Power & Energy"
    TELECOM = "Telecom"
    IT = "IT & Technology"
    CERAMICS = "Ceramics"
    STEEL = "Steel"
    FOOD_ALLIED = "Food & Allied"
    INSURANCE = "Insurance"
    ENGINEERING = "Engineering"
    MISCELLANEOUS = "Miscellaneous"
    UNKNOWN = "Unknown"


@dataclass
class SectorProfile:
    """Sector characteristics and investment notes for Bangladesh context."""
    sector: Sector
    display_name: str

    # Characteristics
    cyclicality: str  # "Low", "Medium", "High"
    defensiveness: bool  # Is it a defensive sector?
    growth_potential: str  # "Low", "Medium", "High"
    bdt_depreciation_impact: str  # "Positive", "Negative", "Neutral"

    # Investment context
    key_characteristics: List[str]
    risks: List[str]
    opportunities: List[str]

    # Verdict
    verdict: str
    investment_note: str

    def to_dict(self) -> Dict:
        return {
            "sector": self.sector.value,
            "display_name": self.display_name,
            "cyclicality": self.cyclicality,
            "is_defensive": self.defensiveness,
            "growth_potential": self.growth_potential,
            "currency_impact": self.bdt_depreciation_impact,
            "characteristics": self.key_characteristics,
            "risks": self.risks,
            "opportunities": self.opportunities,
            "verdict": self.verdict,
            "investment_note": self.investment_note,
        }


# Bangladesh-specific sector profiles
SECTOR_PROFILES: Dict[Sector, SectorProfile] = {
    Sector.PHARMACEUTICALS: SectorProfile(
        sector=Sector.PHARMACEUTICALS,
        display_name="Pharmaceuticals",
        cyclicality="Low",
        defensiveness=True,
        growth_potential="High",
        bdt_depreciation_impact="Neutral",
        key_characteristics=[
            "Captive 170M+ population with growing healthcare needs",
            "97% domestic market served by local manufacturers",
            "Growing exports to US, EU regulated markets",
            "API backward integration reducing import dependency",
        ],
        risks=[
            "API raw material imports from China/India",
            "Regulatory approval delays for exports",
            "R&D investment requirements increasing",
        ],
        opportunities=[
            "Export market expansion (regulated markets)",
            "Aging demographics driving demand",
            "Universal healthcare coverage push",
        ],
        verdict="Defensive + Growth",
        investment_note="One of Bangladesh's strongest sectors. Look for companies with FDA/WHO approvals and export revenue growth.",
    ),

    Sector.BANKING: SectorProfile(
        sector=Sector.BANKING,
        display_name="Banking",
        cyclicality="High",
        defensiveness=False,
        growth_potential="Medium",
        bdt_depreciation_impact="Negative",
        key_characteristics=[
            "High NPL ratios (9-12%) - systemic issue",
            "Interest rate caps recently removed (2023)",
            "Private banks significantly better than state banks",
            "Mobile banking disruption (bKash, Nagad)",
        ],
        risks=[
            "Connected lending and governance issues",
            "NPL provisioning may be understated",
            "Dollar crisis impacted LC margins",
            "Liquidity stress in weaker banks",
        ],
        opportunities=[
            "Interest rate deregulation improving NIM",
            "Digital banking reducing costs",
            "SME lending growth potential",
        ],
        verdict="High Risk/Reward",
        investment_note="Cherry-pick quality private banks only. Avoid state banks and those with governance issues. Check NPL ratios carefully.",
    ),

    Sector.NBFI: SectorProfile(
        sector=Sector.NBFI,
        display_name="Non-Bank Financial Institutions",
        cyclicality="High",
        defensiveness=False,
        growth_potential="Low",
        bdt_depreciation_impact="Negative",
        key_characteristics=[
            "Sector suffered major trust deficit after collapses",
            "Chronic liquidity and funding stress",
            "Bangladesh Bank tightening oversight",
            "Higher cost of funds than banks",
        ],
        risks=[
            "Structural funding mismatch",
            "Asset quality concerns",
            "Limited deposit mobilization ability",
            "Regulatory tightening ongoing",
        ],
        opportunities=[
            "Leasing and SME financing niche",
            "Survivors may consolidate market share",
        ],
        verdict="Avoid/Speculative",
        investment_note="Structural problems persist. Only consider IDLC or Lanka Bangla if governance is priority. Most NBFIs are uninvestable.",
    ),

    Sector.CEMENT: SectorProfile(
        sector=Sector.CEMENT,
        display_name="Cement",
        cyclicality="High",
        defensiveness=False,
        growth_potential="High",
        bdt_depreciation_impact="Negative",
        key_characteristics=[
            "Mega infrastructure projects driving demand (Metro, Padma Rail)",
            "Industry overcapacity (~70% utilization)",
            "100% clinker import dependent",
            "Energy intensive (coal/gas costs critical)",
        ],
        risks=[
            "USD-denominated clinker imports",
            "Energy cost volatility",
            "Overcapacity leading to price wars",
            "Government project payment delays",
        ],
        opportunities=[
            "Infrastructure spending pipeline strong",
            "Urbanization driving housing demand",
            "Industry consolidation potential",
        ],
        verdict="Cyclical",
        investment_note="Tied to infrastructure spending cycle. Cost pressures from imports. Prefer companies with captive power and efficient logistics.",
    ),

    Sector.FMCG: SectorProfile(
        sector=Sector.FMCG,
        display_name="Fast Moving Consumer Goods",
        cyclicality="Low",
        defensiveness=True,
        growth_potential="Medium",
        bdt_depreciation_impact="Slight Negative",
        key_characteristics=[
            "Growing middle class expanding demand",
            "Strong brand loyalty in Bangladesh",
            "Distribution networks create moats",
            "Can pass through costs with some lag",
        ],
        risks=[
            "Raw material import exposure",
            "MNC competition in premium segments",
            "Rural demand sensitive to agriculture",
        ],
        opportunities=[
            "Rural market penetration",
            "Premiumization trend",
            "E-commerce channel growth",
        ],
        verdict="Defensive Compounder",
        investment_note="Steady growth, inflation hedge. Look for companies with strong distribution and pricing power. MARICO, Olympic are quality names.",
    ),

    Sector.TEXTILES_RMG: SectorProfile(
        sector=Sector.TEXTILES_RMG,
        display_name="Textiles & RMG",
        cyclicality="High",
        defensiveness=False,
        growth_potential="Medium",
        bdt_depreciation_impact="Positive",
        key_characteristics=[
            "~85% of Bangladesh's total exports ($45B+ industry)",
            "#2 globally but Vietnam/Cambodia gaining share",
            "Compliance costs rising (green factory, safety)",
            "Backward linkage (spinning, weaving) improving margins",
        ],
        risks=[
            "Order diversification away from Bangladesh",
            "Minimum wage hikes pressuring margins",
            "Buyer concentration risk",
            "Lead time competition with Vietnam",
        ],
        opportunities=[
            "BDT depreciation boosts competitiveness",
            "Green/sustainable factory premiums",
            "Value-added product shift",
        ],
        verdict="Export Play",
        investment_note="Benefits from weak BDT. Look for vertically integrated players with compliance certifications. Margin pressure is ongoing concern.",
    ),

    Sector.POWER_ENERGY: SectorProfile(
        sector=Sector.POWER_ENERGY,
        display_name="Power & Energy",
        cyclicality="Low",
        defensiveness=True,
        growth_potential="Low",
        bdt_depreciation_impact="Negative",
        key_characteristics=[
            "Government-backed PPAs guarantee revenue",
            "Generation overcapacity but distribution bottlenecks",
            "Shifting from gas to LNG/coal (import dependent)",
            "UPGDCL has Dhaka gas distribution monopoly",
        ],
        risks=[
            "Government payment delays",
            "Subsidy and tariff politics",
            "Fuel import cost exposure",
            "Renewable disruption long-term",
        ],
        opportunities=[
            "Stable cash flows from PPAs",
            "Distribution network value",
            "Renewable energy push",
        ],
        verdict="Utility/Defensive",
        investment_note="Predictable but limited growth. UPGDCL is unique monopoly play. IPPs face payment risk. Good for income-focused investors.",
    ),

    Sector.TELECOM: SectorProfile(
        sector=Sector.TELECOM,
        display_name="Telecom",
        cyclicality="Low",
        defensiveness=True,
        growth_potential="Low",
        bdt_depreciation_impact="Neutral",
        key_characteristics=[
            "Oligopoly: GP (45%), Robi, Banglalink",
            "SIM penetration >100% - voice saturated",
            "Data/4G driving revenue growth now",
            "Heavy taxation and regulatory burden",
        ],
        risks=[
            "Regulatory uncertainty (license renewals, taxes)",
            "Price competition in data",
            "Tower sharing reducing capex moat",
        ],
        opportunities=[
            "Data consumption growth",
            "Mobile financial services",
            "Enterprise/B2B segment",
        ],
        verdict="Cash Cow",
        investment_note="Limited growth but strong cash generation. GP is the only listed quality option. Regulatory risks are main concern.",
    ),

    Sector.IT: SectorProfile(
        sector=Sector.IT,
        display_name="IT & Technology",
        cyclicality="Medium",
        defensiveness=False,
        growth_potential="High",
        bdt_depreciation_impact="Positive",
        key_characteristics=[
            "Digital Bangladesh government push",
            "#2 globally in freelancers ($600M+ annual)",
            "Hi-Tech Parks with tax holidays",
            "Very few quality listed options on DSE",
        ],
        risks=[
            "Limited investable listed companies",
            "Talent retention challenges",
            "Global recession impacts outsourcing",
        ],
        opportunities=[
            "Software export growth",
            "Fintech and digital services",
            "Government digitization contracts",
        ],
        verdict="Emerging",
        investment_note="High potential but limited DSE options. Most value creation happening in unlisted startups. Watch for new listings.",
    ),

    Sector.CERAMICS: SectorProfile(
        sector=Sector.CERAMICS,
        display_name="Ceramics & Tiles",
        cyclicality="High",
        defensiveness=False,
        growth_potential="Medium",
        bdt_depreciation_impact="Negative",
        key_characteristics=[
            "Housing boom driving demand",
            "Successful import substitution story",
            "Gas supply critical for production",
            "Growing exports to India, Nepal",
        ],
        risks=[
            "Gas supply disruptions",
            "Real estate cycle dependency",
            "Competition intensifying",
        ],
        opportunities=[
            "Export market expansion",
            "Premium segment growth",
            "Urbanization tailwind",
        ],
        verdict="Cyclical/Real Estate Proxy",
        investment_note="Tied to construction and real estate cycle. Gas availability is key operational risk. FU-WANG, RAK are established players.",
    ),

    Sector.STEEL: SectorProfile(
        sector=Sector.STEEL,
        display_name="Steel",
        cyclicality="High",
        defensiveness=False,
        growth_potential="Medium",
        bdt_depreciation_impact="Highly Negative",
        key_characteristics=[
            "100% raw material imports (scrap, billets)",
            "Infrastructure and real estate driven demand",
            "Fragmented market with price wars",
            "USD costs vs BDT revenues = margin squeeze",
        ],
        risks=[
            "Severe currency exposure",
            "Working capital intensive",
            "Commodity price volatility",
            "Competition from imports",
        ],
        opportunities=[
            "Infrastructure demand pipeline",
            "Industry consolidation",
        ],
        verdict="Avoid in Weak BDT",
        investment_note="Structurally challenged when BDT is weak. Margin compression is ongoing. Only consider in stable currency environment.",
    ),

    Sector.FOOD_ALLIED: SectorProfile(
        sector=Sector.FOOD_ALLIED,
        display_name="Food & Allied",
        cyclicality="Low",
        defensiveness=True,
        growth_potential="Medium",
        bdt_depreciation_impact="Slight Negative",
        key_characteristics=[
            "Essential/defensive - people always eat",
            "Commodity input exposure (wheat, oil, sugar)",
            "Strong brands command premiums",
            "Distribution networks are moats",
        ],
        risks=[
            "Input cost inflation",
            "Import dependency for raw materials",
            "Price sensitivity in mass market",
        ],
        opportunities=[
            "Premiumization and health trends",
            "Rural distribution expansion",
            "Export potential for processed foods",
        ],
        verdict="Defensive",
        investment_note="Inflation hedge with steady demand. Olympic (biscuits), AMCL Pran are established. Look for pricing power and brand strength.",
    ),

    Sector.INSURANCE: SectorProfile(
        sector=Sector.INSURANCE,
        display_name="Insurance",
        cyclicality="Medium",
        defensiveness=False,
        growth_potential="High",
        bdt_depreciation_impact="Neutral",
        key_characteristics=[
            "Very low penetration (<1% of GDP)",
            "Life insurance growing faster than general",
            "Governance issues in many companies",
            "Float provides investment income",
        ],
        risks=[
            "Claims dispute reputation",
            "Governance and related party issues",
            "Regulatory enforcement weak historically",
        ],
        opportunities=[
            "Massive underpenetration runway",
            "Bancassurance partnerships",
            "Health insurance growth",
        ],
        verdict="Growth Potential",
        investment_note="Long runway but quality screening essential. Avoid companies with governance red flags. Delta Life, Green Delta relatively better.",
    ),

    Sector.ENGINEERING: SectorProfile(
        sector=Sector.ENGINEERING,
        display_name="Engineering",
        cyclicality="High",
        defensiveness=False,
        growth_potential="Medium",
        bdt_depreciation_impact="Negative",
        key_characteristics=[
            "Diverse sub-sectors (electrical, mechanical, auto)",
            "Import substitution opportunities",
            "Infrastructure projects create demand",
            "Raw material import dependency varies",
        ],
        risks=[
            "Project-based revenue volatility",
            "Import cost exposure",
            "Technology obsolescence",
        ],
        opportunities=[
            "Local manufacturing push",
            "Infrastructure spending",
            "Export potential in some niches",
        ],
        verdict="Selective",
        investment_note="Pick companies with clear competitive advantages and less import dependency. Singer, Walton (unlisted) are market leaders.",
    ),

    Sector.MISCELLANEOUS: SectorProfile(
        sector=Sector.MISCELLANEOUS,
        display_name="Miscellaneous",
        cyclicality="Varies",
        defensiveness=False,
        growth_potential="Varies",
        bdt_depreciation_impact="Varies",
        key_characteristics=[
            "Diverse companies not fitting other categories",
            "Individual analysis required",
        ],
        risks=["Sector-specific risks vary"],
        opportunities=["Company-specific opportunities"],
        verdict="Case by Case",
        investment_note="Analyze each company individually. No sector-level thesis applies.",
    ),

    Sector.UNKNOWN: SectorProfile(
        sector=Sector.UNKNOWN,
        display_name="Unclassified",
        cyclicality="Unknown",
        defensiveness=False,
        growth_potential="Unknown",
        bdt_depreciation_impact="Unknown",
        key_characteristics=["Sector classification pending"],
        risks=["Unknown sector risks"],
        opportunities=["Unknown"],
        verdict="Needs Classification",
        investment_note="This stock needs sector classification for proper analysis.",
    ),
}


# Stock to Sector mapping - sourced from DSE official classification
# Updated: 2026-01-19
STOCK_SECTOR_MAP: Dict[str, Sector] = {
    # PHARMACEUTICALS
    "ACI": Sector.PHARMACEUTICALS,
    "ACIFORMULA": Sector.PHARMACEUTICALS,
    "ACMELAB": Sector.PHARMACEUTICALS,
    "ACMEPL": Sector.PHARMACEUTICALS,
    "ACTIVEFINE": Sector.PHARMACEUTICALS,
    "ADVENT": Sector.PHARMACEUTICALS,
    "AFCAGRO": Sector.PHARMACEUTICALS,
    "AMBEEPHA": Sector.PHARMACEUTICALS,
    "ASIATICLAB": Sector.PHARMACEUTICALS,
    "BEACONPHAR": Sector.PHARMACEUTICALS,
    "BXPHARMA": Sector.PHARMACEUTICALS,
    "CENTRALPHL": Sector.PHARMACEUTICALS,
    "FARCHEM": Sector.PHARMACEUTICALS,
    "GHCL": Sector.PHARMACEUTICALS,
    "IBNSINA": Sector.PHARMACEUTICALS,
    "IBP": Sector.PHARMACEUTICALS,
    "JHRML": Sector.PHARMACEUTICALS,
    "JMISMDL": Sector.PHARMACEUTICALS,
    "KEYACOSMET": Sector.PHARMACEUTICALS,
    "KOHINOOR": Sector.PHARMACEUTICALS,
    "LIBRAINFU": Sector.PHARMACEUTICALS,
    "MARICO": Sector.PHARMACEUTICALS,
    "NAVANAPHAR": Sector.PHARMACEUTICALS,
    "ORIONINFU": Sector.PHARMACEUTICALS,
    "ORIONPHARM": Sector.PHARMACEUTICALS,
    "PHARMAID": Sector.PHARMACEUTICALS,
    "RECKITTBEN": Sector.PHARMACEUTICALS,
    "RENATA": Sector.PHARMACEUTICALS,
    "SALVO": Sector.PHARMACEUTICALS,
    "SILCOPHL": Sector.PHARMACEUTICALS,
    "SILVAPHL": Sector.PHARMACEUTICALS,
    "SQURPHARMA": Sector.PHARMACEUTICALS,
    "TECHNODRUG": Sector.PHARMACEUTICALS,
    "WATACHEM": Sector.PHARMACEUTICALS,

    # BANKING
    "ABBANK": Sector.BANKING,
    "ALARABANK": Sector.BANKING,
    "BANKASIA": Sector.BANKING,
    "BRACBANK": Sector.BANKING,
    "CITYBANK": Sector.BANKING,
    "DHAKABANK": Sector.BANKING,
    "DUTCHBANGL": Sector.BANKING,
    "EBL": Sector.BANKING,
    "EXIMBANK": Sector.BANKING,
    "FIRSTSBANK": Sector.BANKING,
    "GIB": Sector.BANKING,
    "ICBIBANK": Sector.BANKING,
    "IFIC": Sector.BANKING,
    "ISLAMIBANK": Sector.BANKING,
    "JAMUNABANK": Sector.BANKING,
    "MERCANBANK": Sector.BANKING,
    "MIDLANDBNK": Sector.BANKING,
    "MTB": Sector.BANKING,
    "NBL": Sector.BANKING,
    "NCCBANK": Sector.BANKING,
    "NRBBANK": Sector.BANKING,
    "NRBCBANK": Sector.BANKING,
    "ONEBANKPLC": Sector.BANKING,
    "PREMIERBAN": Sector.BANKING,
    "PRIMEBANK": Sector.BANKING,
    "PUBALIBANK": Sector.BANKING,
    "RUPALIBANK": Sector.BANKING,
    "SBACBANK": Sector.BANKING,
    "SHAHJABANK": Sector.BANKING,
    "SIBL": Sector.BANKING,
    "SOUTHEASTB": Sector.BANKING,
    "STANDBANKL": Sector.BANKING,
    "TRUSTBANK": Sector.BANKING,
    "UCB": Sector.BANKING,
    "UNIONBANK": Sector.BANKING,
    "UTTARABANK": Sector.BANKING,

    # NBFI
    "BAYLEASING": Sector.NBFI,
    "BDFINANCE": Sector.NBFI,
    "BIFC": Sector.NBFI,
    "DBH": Sector.NBFI,
    "FAREASTFIN": Sector.NBFI,
    "FASFIN": Sector.NBFI,
    "FIRSTFIN": Sector.NBFI,
    "GSPFINANCE": Sector.NBFI,
    "ICB": Sector.NBFI,
    "IDLC": Sector.NBFI,
    "ILFSL": Sector.NBFI,
    "IPDC": Sector.NBFI,
    "ISLAMICFIN": Sector.NBFI,
    "LANKABAFIN": Sector.NBFI,
    "MIDASFIN": Sector.NBFI,
    "NHFIL": Sector.NBFI,
    "PHOENIXFIN": Sector.NBFI,
    "PLFSL": Sector.NBFI,
    "PREMIERLEA": Sector.NBFI,
    "PRIMEFIN": Sector.NBFI,
    "UNIONCAP": Sector.NBFI,
    "UNITEDFIN": Sector.NBFI,
    "UTTARAFIN": Sector.NBFI,

    # CEMENT
    "ARAMITCEM": Sector.CEMENT,
    "CONFIDCEM": Sector.CEMENT,
    "CROWNCEMNT": Sector.CEMENT,
    "HEIDELBCEM": Sector.CEMENT,
    "LHB": Sector.CEMENT,
    "MEGHNACEM": Sector.CEMENT,
    "PREMIERCEM": Sector.CEMENT,

    # TEXTILES_RMG
    "ACFL": Sector.TEXTILES_RMG,
    "AIL": Sector.TEXTILES_RMG,
    "AL-HAJTEX": Sector.TEXTILES_RMG,
    "ALIF": Sector.TEXTILES_RMG,
    "ALLTEX": Sector.TEXTILES_RMG,
    "ANLIMAYARN": Sector.TEXTILES_RMG,
    "APEXFOOT": Sector.TEXTILES_RMG,
    "APEXSPINN": Sector.TEXTILES_RMG,
    "APEXTANRY": Sector.TEXTILES_RMG,
    "ARGONDENIM": Sector.TEXTILES_RMG,
    "BATASHOE": Sector.TEXTILES_RMG,
    "CNATEX": Sector.TEXTILES_RMG,
    "DACCADYE": Sector.TEXTILES_RMG,
    "DSHGARME": Sector.TEXTILES_RMG,
    "DSSL": Sector.TEXTILES_RMG,
    "DELTASPINN": Sector.TEXTILES_RMG,
    "DULAMIACOT": Sector.TEXTILES_RMG,
    "ENVOYTEX": Sector.TEXTILES_RMG,
    "ESQUIRENIT": Sector.TEXTILES_RMG,
    "ETL": Sector.TEXTILES_RMG,
    "FAMILYTEX": Sector.TEXTILES_RMG,
    "FEKDIL": Sector.TEXTILES_RMG,
    "FORTUNE": Sector.TEXTILES_RMG,
    "GENNEXT": Sector.TEXTILES_RMG,
    "HFL": Sector.TEXTILES_RMG,
    "HRTEX": Sector.TEXTILES_RMG,
    "HWAWELLTEX": Sector.TEXTILES_RMG,
    "KTL": Sector.TEXTILES_RMG,
    "JUTESPINN": Sector.TEXTILES_RMG,
    "LEGACYFOOT": Sector.TEXTILES_RMG,
    "MAKSONSPIN": Sector.TEXTILES_RMG,
    "MALEKSPIN": Sector.TEXTILES_RMG,
    "MATINSPINN": Sector.TEXTILES_RMG,
    "METROSPIN": Sector.TEXTILES_RMG,
    "MHSML": Sector.TEXTILES_RMG,
    "MITHUNKNIT": Sector.TEXTILES_RMG,
    "MLDYEING": Sector.TEXTILES_RMG,
    "MONNOFABR": Sector.TEXTILES_RMG,
    "NEWLINE": Sector.TEXTILES_RMG,
    "NORTHERN": Sector.TEXTILES_RMG,
    "NURANI": Sector.TEXTILES_RMG,
    "PDL": Sector.TEXTILES_RMG,
    "PRIMETEX": Sector.TEXTILES_RMG,
    "PTL": Sector.TEXTILES_RMG,
    "QUEENSOUTH": Sector.TEXTILES_RMG,
    "RAHIMTEXT": Sector.TEXTILES_RMG,
    "REGENTTEX": Sector.TEXTILES_RMG,
    "RINGSHINE": Sector.TEXTILES_RMG,
    "SAFKOSPINN": Sector.TEXTILES_RMG,
    "SAIHAMCOT": Sector.TEXTILES_RMG,
    "SAIHAMTEX": Sector.TEXTILES_RMG,
    "SAMATALETH": Sector.TEXTILES_RMG,
    "SHARPIND": Sector.TEXTILES_RMG,
    "SHASHADNIM": Sector.TEXTILES_RMG,
    "SHEPHERD": Sector.TEXTILES_RMG,
    "SIMTEX": Sector.TEXTILES_RMG,
    "SONALIANSH": Sector.TEXTILES_RMG,
    "SONARGAON": Sector.TEXTILES_RMG,
    "SQUARETEXT": Sector.TEXTILES_RMG,
    "STYLECRAFT": Sector.TEXTILES_RMG,
    "TALLUSPIN": Sector.TEXTILES_RMG,
    "TAMIJTEX": Sector.TEXTILES_RMG,
    "TOSRIFA": Sector.TEXTILES_RMG,
    "TUNGHAI": Sector.TEXTILES_RMG,
    "VFSTDL": Sector.TEXTILES_RMG,
    "ZAHEENSPIN": Sector.TEXTILES_RMG,
    "ZAHINTEX": Sector.TEXTILES_RMG,

    # POWER_ENERGY
    "AOL": Sector.POWER_ENERGY,
    "BARKAPOWER": Sector.POWER_ENERGY,
    "BDWELDING": Sector.POWER_ENERGY,
    "BPPL": Sector.POWER_ENERGY,
    "CVOPRL": Sector.POWER_ENERGY,
    "DESCO": Sector.POWER_ENERGY,
    "DOREENPWR": Sector.POWER_ENERGY,
    "EASTRNLUB": Sector.POWER_ENERGY,
    "EPGL": Sector.POWER_ENERGY,
    "GBBPOWER": Sector.POWER_ENERGY,
    "INTRACO": Sector.POWER_ENERGY,
    "JAMUNAOIL": Sector.POWER_ENERGY,
    "KPCL": Sector.POWER_ENERGY,
    "LINDEBD": Sector.POWER_ENERGY,
    "LRBDL": Sector.POWER_ENERGY,
    "MJLBD": Sector.POWER_ENERGY,
    "MPETROLEUM": Sector.POWER_ENERGY,
    "PADMAOIL": Sector.POWER_ENERGY,
    "POWERGRID": Sector.POWER_ENERGY,
    "SPCL": Sector.POWER_ENERGY,
    "SUMITPOWER": Sector.POWER_ENERGY,
    "TITASGAS": Sector.POWER_ENERGY,
    "UPGDCL": Sector.POWER_ENERGY,

    # TELECOM
    "BSCPLC": Sector.TELECOM,
    "GP": Sector.TELECOM,
    "ROBI": Sector.TELECOM,

    # IT
    "AAMRANET": Sector.IT,
    "AAMRATECH": Sector.IT,
    "ADNTEL": Sector.IT,
    "AGNISYSL": Sector.IT,
    "BDCOM": Sector.IT,
    "DAFODILCOM": Sector.IT,
    "EGEN": Sector.IT,
    "GENEXIL": Sector.IT,
    "INTECH": Sector.IT,
    "ISNLTD": Sector.IT,
    "ITC": Sector.IT,

    # CERAMICS
    "FUWANGCER": Sector.CERAMICS,
    "MONNOCERA": Sector.CERAMICS,
    "RAKCERAMIC": Sector.CERAMICS,
    "SPCERAMICS": Sector.CERAMICS,
    "STANCERAM": Sector.CERAMICS,

    # FOOD_ALLIED
    "AMCL(PRAN)": Sector.FOOD_ALLIED,
    "APEXFOODS": Sector.FOOD_ALLIED,
    "BANGAS": Sector.FOOD_ALLIED,
    "BATBC": Sector.FOOD_ALLIED,
    "BDTHAIFOOD": Sector.FOOD_ALLIED,
    "BEACHHATCH": Sector.FOOD_ALLIED,
    "EMERALDOIL": Sector.FOOD_ALLIED,
    "FINEFOODS": Sector.FOOD_ALLIED,
    "FUWANGFOOD": Sector.FOOD_ALLIED,
    "GEMINISEA": Sector.FOOD_ALLIED,
    "GHAIL": Sector.FOOD_ALLIED,
    "LOVELLO": Sector.FOOD_ALLIED,
    "MEGCONMILK": Sector.FOOD_ALLIED,
    "MEGHNAPET": Sector.FOOD_ALLIED,
    "NTC": Sector.FOOD_ALLIED,
    "OLYMPIC": Sector.FOOD_ALLIED,
    "RAHIMAFOOD": Sector.FOOD_ALLIED,
    "RDFOOD": Sector.FOOD_ALLIED,
    "SHYAMPSUG": Sector.FOOD_ALLIED,
    "UNILEVERCL": Sector.FOOD_ALLIED,
    "ZEALBANGLA": Sector.FOOD_ALLIED,

    # INSURANCE
    "AGRANINS": Sector.INSURANCE,
    "ASIAINS": Sector.INSURANCE,
    "ASIAPACINS": Sector.INSURANCE,
    "BGIC": Sector.INSURANCE,
    "BNICL": Sector.INSURANCE,
    "CENTRALINS": Sector.INSURANCE,
    "CITYGENINS": Sector.INSURANCE,
    "CLICL": Sector.INSURANCE,
    "CONTININS": Sector.INSURANCE,
    "CRYSTALINS": Sector.INSURANCE,
    "DELTALIFE": Sector.INSURANCE,
    "DGIC": Sector.INSURANCE,
    "DHAKAINS": Sector.INSURANCE,
    "EASTERNINS": Sector.INSURANCE,
    "EASTLAND": Sector.INSURANCE,
    "EIL": Sector.INSURANCE,
    "FAREASTLIF": Sector.INSURANCE,
    "FEDERALINS": Sector.INSURANCE,
    "GLOBALINS": Sector.INSURANCE,
    "GREENDELT": Sector.INSURANCE,
    "ICICL": Sector.INSURANCE,
    "ISLAMIINS": Sector.INSURANCE,
    "JANATAINS": Sector.INSURANCE,
    "KARNAPHULI": Sector.INSURANCE,
    "MEGHNAINS": Sector.INSURANCE,
    "MEGHNALIFE": Sector.INSURANCE,
    "MERCINS": Sector.INSURANCE,
    "NATLIFEINS": Sector.INSURANCE,
    "NITOLINS": Sector.INSURANCE,
    "NORTHRNINS": Sector.INSURANCE,
    "PADMALIFE": Sector.INSURANCE,
    "PARAMOUNT": Sector.INSURANCE,
    "PEOPLESINS": Sector.INSURANCE,
    "PHENIXINS": Sector.INSURANCE,
    "PIONEERINS": Sector.INSURANCE,
    "POPULARLIF": Sector.INSURANCE,
    "PRAGATIINS": Sector.INSURANCE,
    "PRAGATILIF": Sector.INSURANCE,
    "PRIMEINSUR": Sector.INSURANCE,
    "PRIMELIFE": Sector.INSURANCE,
    "PROGRESLIF": Sector.INSURANCE,
    "PROVATIINS": Sector.INSURANCE,
    "PURABIGEN": Sector.INSURANCE,
    "RELIANCINS": Sector.INSURANCE,
    "REPUBLIC": Sector.INSURANCE,
    "RUPALIINS": Sector.INSURANCE,
    "RUPALILIFE": Sector.INSURANCE,
    "SANDHANINS": Sector.INSURANCE,
    "SICL": Sector.INSURANCE,
    "SIPLC": Sector.INSURANCE,
    "SONALILIFE": Sector.INSURANCE,
    "SONARBAINS": Sector.INSURANCE,
    "STANDARINS": Sector.INSURANCE,
    "SUNLIFEINS": Sector.INSURANCE,
    "TAKAFULINS": Sector.INSURANCE,
    "TILIL": Sector.INSURANCE,
    "UNIONINS": Sector.INSURANCE,
    "UNITEDINS": Sector.INSURANCE,

    # ENGINEERING
    "AFTABAUTO": Sector.ENGINEERING,
    "ANWARGALV": Sector.ENGINEERING,
    "APOLOISPAT": Sector.ENGINEERING,
    "ATLASBANG": Sector.ENGINEERING,
    "AZIZPIPES": Sector.ENGINEERING,
    "BBS": Sector.ENGINEERING,
    "BBSCABLES": Sector.ENGINEERING,
    "BDAUTOCA": Sector.ENGINEERING,
    "BDLAMPS": Sector.ENGINEERING,
    "BDTHAI": Sector.ENGINEERING,
    "BENGALWTL": Sector.ENGINEERING,
    "BSRMLTD": Sector.ENGINEERING,
    "BSRMSTEEL": Sector.ENGINEERING,
    "COPPERTECH": Sector.ENGINEERING,
    "DESHBANDHU": Sector.ENGINEERING,
    "DOMINAGE": Sector.ENGINEERING,
    "ECABLES": Sector.ENGINEERING,
    "GOLDENSON": Sector.ENGINEERING,
    "GPHISPAT": Sector.ENGINEERING,
    "IFADAUTOS": Sector.ENGINEERING,
    "KAY&QUE": Sector.ENGINEERING,
    "KDSALTD": Sector.ENGINEERING,
    "MIRAKHTER": Sector.ENGINEERING,
    "MONNOAGML": Sector.ENGINEERING,
    "NAHEEACP": Sector.ENGINEERING,
    "NAVANACNG": Sector.ENGINEERING,
    "NPOLYMER": Sector.ENGINEERING,
    "NTLTUBES": Sector.ENGINEERING,
    "OAL": Sector.ENGINEERING,
    "OIMEX": Sector.ENGINEERING,
    "QUASEMIND": Sector.ENGINEERING,
    "RANFOUNDRY": Sector.ENGINEERING,
    "RENWICKJA": Sector.ENGINEERING,
    "RSRMSTEEL": Sector.ENGINEERING,
    "RUNNERAUTO": Sector.ENGINEERING,
    "SALAMCRST": Sector.ENGINEERING,
    "SHURWID": Sector.ENGINEERING,
    "SINGERBD": Sector.ENGINEERING,
    "SSSTEEL": Sector.ENGINEERING,
    "WALTONHIL": Sector.ENGINEERING,
    "WMSHIPYARD": Sector.ENGINEERING,
    "YPL": Sector.ENGINEERING,

    # MISCELLANEOUS
    "AMANFEED": Sector.MISCELLANEOUS,
    "ARAMIT": Sector.MISCELLANEOUS,
    "BDSERVICE": Sector.MISCELLANEOUS,
    "BERGERPBL": Sector.MISCELLANEOUS,
    "BESTHLDNG": Sector.MISCELLANEOUS,
    "BEXIMCO": Sector.MISCELLANEOUS,
    "BPML": Sector.MISCELLANEOUS,
    "BSC": Sector.MISCELLANEOUS,
    "EHL": Sector.MISCELLANEOUS,
    "GQBALLPEN": Sector.MISCELLANEOUS,
    "HAKKANIPUL": Sector.MISCELLANEOUS,
    "HAMI": Sector.MISCELLANEOUS,
    "INDEXAGRO": Sector.MISCELLANEOUS,
    "KBPPWBIL": Sector.MISCELLANEOUS,
    "KPPL": Sector.MISCELLANEOUS,
    "MAGURAPLEX": Sector.MISCELLANEOUS,
    "MIRACLEIND": Sector.MISCELLANEOUS,
    "MONOSPOOL": Sector.MISCELLANEOUS,
    "NFML": Sector.MISCELLANEOUS,
    "PENINSULA": Sector.MISCELLANEOUS,
    "SAIFPOWER": Sector.MISCELLANEOUS,
    "SAMORITA": Sector.MISCELLANEOUS,
    "SAPORTL": Sector.MISCELLANEOUS,
    "SAVAREFR": Sector.MISCELLANEOUS,
    "SEAPEARL": Sector.MISCELLANEOUS,
    "SINOBANGLA": Sector.MISCELLANEOUS,
    "SKTRIMS": Sector.MISCELLANEOUS,
    "SONALIPAPR": Sector.MISCELLANEOUS,
    "UNIQUEHRL": Sector.MISCELLANEOUS,
    "USMANIAGL": Sector.MISCELLANEOUS,
}


def get_sector(symbol: str) -> Sector:
    """Get sector for a stock symbol."""
    return STOCK_SECTOR_MAP.get(symbol.upper(), Sector.UNKNOWN)


def get_sector_profile(symbol: str) -> SectorProfile:
    """Get full sector profile for a stock symbol."""
    sector = get_sector(symbol)
    return SECTOR_PROFILES.get(sector, SECTOR_PROFILES[Sector.UNKNOWN])


def get_sector_note(symbol: str) -> str:
    """Get a concise sector investment note for display."""
    profile = get_sector_profile(symbol)
    return profile.investment_note


def get_sector_summary(symbol: str) -> Dict:
    """Get sector summary for API response."""
    profile = get_sector_profile(symbol)
    return {
        "sector": profile.sector.value,
        "cyclicality": profile.cyclicality,
        "is_defensive": profile.defensiveness,
        "growth_potential": profile.growth_potential,
        "currency_impact": profile.bdt_depreciation_impact,
        "verdict": profile.verdict,
        "note": profile.investment_note,
        "key_points": profile.key_characteristics[:3],  # Top 3 characteristics
        "main_risk": profile.risks[0] if profile.risks else None,
    }
