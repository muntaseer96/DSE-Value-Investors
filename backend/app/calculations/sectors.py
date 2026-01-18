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


# Stock to Sector mapping for known DSE stocks
STOCK_SECTOR_MAP: Dict[str, Sector] = {
    # Pharmaceuticals
    "BXPHARMA": Sector.PHARMACEUTICALS,
    "SQURPHARMA": Sector.PHARMACEUTICALS,
    "BEXIMCO": Sector.PHARMACEUTICALS,  # Diversified but pharma-heavy
    "RENATA": Sector.PHARMACEUTICALS,
    "ACIFORMULA": Sector.PHARMACEUTICALS,
    "IBNSINA": Sector.PHARMACEUTICALS,
    "GLAXOSMITH": Sector.PHARMACEUTICALS,
    "ACTIVEFINE": Sector.PHARMACEUTICALS,
    "BAFPHARMA": Sector.PHARMACEUTICALS,
    "CENTRALPHL": Sector.PHARMACEUTICALS,
    "GLOBALINS": Sector.PHARMACEUTICALS,
    "IMAMBUTTON": Sector.PHARMACEUTICALS,
    "KOABORPHA": Sector.PHARMACEUTICALS,
    "LIBRAINFU": Sector.PHARMACEUTICALS,
    "ORIONINFU": Sector.PHARMACEUTICALS,
    "PHARMA": Sector.PHARMACEUTICALS,
    "SILCOPHL": Sector.PHARMACEUTICALS,

    # Banking
    "BRACBANK": Sector.BANKING,
    "CITYBANK": Sector.BANKING,
    "EBL": Sector.BANKING,
    "DUTCHBANGL": Sector.BANKING,
    "PRIMEBANK": Sector.BANKING,
    "ISLAMIBANK": Sector.BANKING,
    "PUBALIBANK": Sector.BANKING,
    "UTTARABANK": Sector.BANKING,
    "UCBL": Sector.BANKING,
    "MTBL": Sector.BANKING,
    "ONEBANKLTD": Sector.BANKING,
    "BANKASIA": Sector.BANKING,
    "DHAKABANK": Sector.BANKING,
    "ABORIENTB": Sector.BANKING,
    "ALARAB": Sector.BANKING,
    "EXIMBANKBD": Sector.BANKING,
    "IFICBANK": Sector.BANKING,
    "JAMUNABANK": Sector.BANKING,
    "MERCANBANK": Sector.BANKING,
    "NCCBANK": Sector.BANKING,
    "PREMIERBNK": Sector.BANKING,
    "RUPALIBANK": Sector.BANKING,
    "SHAHJABANK": Sector.BANKING,
    "SIBL": Sector.BANKING,
    "SOUTHEASTB": Sector.BANKING,
    "STANDARBNK": Sector.BANKING,
    "TRUSTBANK": Sector.BANKING,

    # NBFI
    "IDLC": Sector.NBFI,
    "LANKABAFIN": Sector.NBFI,
    "IPDC": Sector.NBFI,
    "UTTARFIN": Sector.NBFI,
    "BIFC": Sector.NBFI,
    "BDFINANCE": Sector.NBFI,
    "DELTABFIC": Sector.NBFI,
    "FAREASTFIN": Sector.NBFI,
    "GABORIENTF": Sector.NBFI,
    "GSP": Sector.NBFI,
    "ICBAMCPF": Sector.NBFI,
    "ILFSL": Sector.NBFI,
    "ISLAMICFIN": Sector.NBFI,
    "NHFIL": Sector.NBFI,
    "PHOENIXFIN": Sector.NBFI,
    "PLFS": Sector.NBFI,
    "PREMIERLEA": Sector.NBFI,
    "UNITEDFIN": Sector.NBFI,

    # Cement
    "HEIDELBERG": Sector.CEMENT,
    "LAFARGECEM": Sector.CEMENT,
    "CROWNCEM": Sector.CEMENT,
    "CONFIANCE": Sector.CEMENT,
    "MICEMENT": Sector.CEMENT,
    "PREMIERCEM": Sector.CEMENT,
    "SHYAMCEM": Sector.CEMENT,

    # FMCG
    "MARICO": Sector.FMCG,
    "RECKITTBEN": Sector.FMCG,
    "BATBC": Sector.FMCG,
    "OLYMPIC": Sector.FMCG,
    "ACI": Sector.FMCG,  # Diversified
    "KEYACOS": Sector.FMCG,
    "KOABORPHA": Sector.FMCG,

    # Textiles/RMG
    "SQUARETEXT": Sector.TEXTILES_RMG,
    "ENVOY": Sector.TEXTILES_RMG,
    "DHAKATEX": Sector.TEXTILES_RMG,
    "MALEK": Sector.TEXTILES_RMG,
    "ANLIMAYARN": Sector.TEXTILES_RMG,
    "APEXFOOT": Sector.TEXTILES_RMG,
    "APEXSPINN": Sector.TEXTILES_RMG,
    "APEXTANRY": Sector.TEXTILES_RMG,
    "ATCSLGAZ": Sector.TEXTILES_RMG,
    "BDTHAI": Sector.TEXTILES_RMG,
    "CVOPRL": Sector.TEXTILES_RMG,
    "DELTASPINN": Sector.TEXTILES_RMG,
    "DESHGARME": Sector.TEXTILES_RMG,
    "FAMILYTEX": Sector.TEXTILES_RMG,
    "GENNEXT": Sector.TEXTILES_RMG,
    "HFL": Sector.TEXTILES_RMG,
    "HRTEX": Sector.TEXTILES_RMG,
    "MAKSONS": Sector.TEXTILES_RMG,
    "MATIN": Sector.TEXTILES_RMG,
    "METROSPIN": Sector.TEXTILES_RMG,
    "NORTHERN": Sector.TEXTILES_RMG,
    "NURANI": Sector.TEXTILES_RMG,
    "PRIMETEX": Sector.TEXTILES_RMG,
    "RAHIMTEXT": Sector.TEXTILES_RMG,
    "RAHIM": Sector.TEXTILES_RMG,
    "SAIHAMCOT": Sector.TEXTILES_RMG,
    "SAIHAMTEX": Sector.TEXTILES_RMG,
    "SHEPHERD": Sector.TEXTILES_RMG,
    "SONARGAON": Sector.TEXTILES_RMG,
    "STYLECRAFT": Sector.TEXTILES_RMG,
    "TALLUSPIN": Sector.TEXTILES_RMG,
    "TOSRIFA": Sector.TEXTILES_RMG,
    "ZAHEENSPIN": Sector.TEXTILES_RMG,

    # Power & Energy
    "UPGDCL": Sector.POWER_ENERGY,
    "POWERGRID": Sector.POWER_ENERGY,
    "TITASGAS": Sector.POWER_ENERGY,
    "JAMUNAOIL": Sector.POWER_ENERGY,
    "PADMAOIL": Sector.POWER_ENERGY,
    "MPETROL": Sector.POWER_ENERGY,
    "SUMMITP": Sector.POWER_ENERGY,
    "DESCO": Sector.POWER_ENERGY,
    "KPCL": Sector.POWER_ENERGY,
    "LINDE": Sector.POWER_ENERGY,

    # Telecom
    "GP": Sector.TELECOM,
    "ROBI": Sector.TELECOM,

    # IT
    "BDCOM": Sector.IT,
    "ADNTEL": Sector.IT,
    "AAMRANET": Sector.IT,
    "AAMRATECH": Sector.IT,
    "DATASOFT": Sector.IT,
    "GENEXIL": Sector.IT,
    "INTECH": Sector.IT,

    # Ceramics
    "FUWANGCER": Sector.CERAMICS,
    "FUWANGFOD": Sector.CERAMICS,
    "MONNOCER": Sector.CERAMICS,
    "MONNOCERA": Sector.CERAMICS,
    "RAK": Sector.CERAMICS,
    "STANCERAM": Sector.CERAMICS,

    # Steel
    "BSRMSTEEL": Sector.STEEL,
    "GPHISPAT": Sector.STEEL,
    "KBSB": Sector.STEEL,
    "RSRMSTEEL": Sector.STEEL,
    "ISLAMICLST": Sector.STEEL,

    # Food & Allied
    "AMCL": Sector.FOOD_ALLIED,  # Pran
    "ACIFL": Sector.FOOD_ALLIED,
    "APEXFOODS": Sector.FOOD_ALLIED,
    "FINEFOODS": Sector.FOOD_ALLIED,
    "MEGHNAPET": Sector.FOOD_ALLIED,
    "NORTHERN": Sector.FOOD_ALLIED,
    "SILKBANK": Sector.FOOD_ALLIED,

    # Insurance
    "DELTALIFE": Sector.INSURANCE,
    "GREENDELT": Sector.INSURANCE,
    "POPULAR1LI": Sector.INSURANCE,
    "AGRANINS": Sector.INSURANCE,
    "ASIAINS": Sector.INSURANCE,
    "BGIC": Sector.INSURANCE,
    "CENTRINS": Sector.INSURANCE,
    "DHAKAINSUR": Sector.INSURANCE,
    "EASTERNINS": Sector.INSURANCE,
    "FEDERALINS": Sector.INSURANCE,
    "GLOBINSUR": Sector.INSURANCE,
    "JANATAAINS": Sector.INSURANCE,
    "KABORINSUR": Sector.INSURANCE,
    "MEGHNALIFE": Sector.INSURANCE,
    "MERCANINS": Sector.INSURANCE,
    "NATLIFEINS": Sector.INSURANCE,
    "NITOLINS": Sector.INSURANCE,
    "PARGOCINS": Sector.INSURANCE,
    "PHENIXINS": Sector.INSURANCE,
    "PIONEERINS": Sector.INSURANCE,
    "PRIMEINS": Sector.INSURANCE,
    "PROGINS": Sector.INSURANCE,
    "PURABIGENE": Sector.INSURANCE,
    "RELIANCINS": Sector.INSURANCE,
    "RUPALIINS": Sector.INSURANCE,
    "SANDHANINS": Sector.INSURANCE,
    "SONALILIFE": Sector.INSURANCE,
    "SOUTHEASTINS": Sector.INSURANCE,
    "STANDARINS": Sector.INSURANCE,
    "TAKAFULINS": Sector.INSURANCE,
    "TRUSTBLIFE": Sector.INSURANCE,
    "UNIONINS": Sector.INSURANCE,

    # Engineering
    "SINGERBD": Sector.ENGINEERING,
    "RANGERBD": Sector.ENGINEERING,
    "BATASHOW": Sector.ENGINEERING,
    "QUASEMIND": Sector.ENGINEERING,
    "BDLAMPS": Sector.ENGINEERING,
    "NAHEEACP": Sector.ENGINEERING,
    "RUNNERAUTO": Sector.ENGINEERING,
    "ATLASBANG": Sector.ENGINEERING,
    "BENGALWTL": Sector.ENGINEERING,
    "DACCADYE": Sector.ENGINEERING,
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
