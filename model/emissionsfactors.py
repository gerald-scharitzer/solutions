"""Emissions Factors module.

Conversions and lookups useful in converting to CO2 equivalents,
and other factors relating to emissions and pollutants.
"""

from functools import lru_cache
import enum
import pandas as pd


from model.data_handler import DataHandler
from model.decorators import data_func

CO2EQ_SOURCE = enum.Enum('CO2EQ_SOURCE', 'AR5_WITH_FEEDBACK AR4 SAR')
GRID_SOURCE = enum.Enum('GRID_SOURCE', 'META IPCC')
GRID_RANGE = enum.Enum('GRID_RANGE', 'MEAN HIGH LOW')


class CO2Equiv:
    """Convert CH4/N2O/etc to equivalent CO2.

    conversion_source: which standard conversion model to follow:
       AR5 with feedback: value used in the IPCC 5th Assessment Report,
         as amended with feedback. This is the preferred selection.
       AR4: as used in the IPCC 4th Assessment Report.
       SAR: as used in the IPCC Second Assessment Report.
    """
    def __init__(self, conversion_source=None):
        self.conversion_source = conversion_source if conversion_source else CO2EQ_SOURCE.AR5_WITH_FEEDBACK
        if self.conversion_source == CO2EQ_SOURCE.AR5_WITH_FEEDBACK:
            self.CH4multiplier = 34
            self.N2Omultiplier = 298
        elif self.conversion_source == CO2EQ_SOURCE.AR4:
            self.CH4multiplier = 25
            self.N2Omultiplier = 298
        elif self.conversion_source == CO2EQ_SOURCE.SAR:
            self.CH4multiplier = 21
            self.N2Omultiplier = 310
        else:
            raise ValueError("invalid conversion_source=" + str(self.conversion_source))


def string_to_conversion_source(text):
    """Convert the text strings passed from the Excel implementation of the models
       to the enumerated type defined in this module.
       "Advanced Controls"!I185
    """
    if str(text).lower() == "ar5 with feedback":
        return CO2EQ_SOURCE.AR5_WITH_FEEDBACK
    elif str(text).lower() == "ar5_with_feedback":
        return CO2EQ_SOURCE.AR5_WITH_FEEDBACK
    elif str(text).lower() == "ar4":
        return CO2EQ_SOURCE.AR4
    elif str(text).lower() == "sar":
        return CO2EQ_SOURCE.SAR
    else:
        raise ValueError("invalid conversion name=" + str(text))


def string_to_emissions_grid_source(text):
    """Convert the text strings passed from the Excel implementation of the models
       to the enumerated type defined in this module.
       "Advanced Controls"!C189
    """
    if str(text).lower() == "meta-analysis":
        return GRID_SOURCE.META
    elif str(text).lower() == "meta_analysis":
        return GRID_SOURCE.META
    elif str(text).lower() == "meta analysis":
        return GRID_SOURCE.META
    elif str(text).lower() == "ipcc only":
        return GRID_SOURCE.IPCC
    elif str(text).lower() == "ipcc_only":
        return GRID_SOURCE.IPCC
    else:
        raise ValueError("invalid grid source name=" + str(text))


def string_to_emissions_grid_range(text):
    """Convert the text strings passed from the Excel implementation of the models
       to the enumerated type defined in this module.
       "Advanced Controls"!D189
    """
    if str(text).lower() == "mean":
        return GRID_RANGE.MEAN
    elif str(text).lower() == "median":
        return GRID_RANGE.MEAN
    elif str(text).lower() == "high":
        return GRID_RANGE.HIGH
    elif str(text).lower() == "low":
        return GRID_RANGE.LOW
    else:
        raise ValueError("invalid grid range name=" + str(text))


class ElectricityGenOnGrid(DataHandler):
    def __init__(self, ac, grid_emissions_version=1):
        self.ac = ac
        self.grid_emissions_version = grid_emissions_version

    @lru_cache()
    @data_func
    def conv_ref_grid_CO2eq_per_KWh(self):
        """Grid emission factors (kg CO2-eq per kwh) derived from the AMPERE 3
           MESSAGE Base model. Grid emission factors are fixed at 2015 levels
           to reflect the REF case (e.g. no significant technological change).

           'Emissions Factors'!A11:K57
        """
        result = pd.DataFrame(index=list(range(2015, 2061)),
                              columns=["World", "OECD90", "Eastern Europe", "Asia (Sans Japan)",
                                       "Middle East and Africa", "Latin America", "China", "India",
                                       "EU", "USA"])
        result.index.name = "Year"
        if self.ac.emissions_grid_source == GRID_SOURCE.IPCC:
            grid = _world_ipcc
        elif self.ac.emissions_grid_source == GRID_SOURCE.META and self.grid_emissions_version == 1:
            grid = _world_meta_1
        elif self.ac.emissions_grid_source == GRID_SOURCE.META and self.grid_emissions_version == 2:
            grid = _world_meta_2
        elif self.ac.emissions_grid_source == GRID_SOURCE.META and self.grid_emissions_version == 3:
            grid = _world_meta_3
        elif self.ac.emissions_grid_source == GRID_SOURCE.META and self.grid_emissions_version == 4:
            grid = _world_meta_4
        else:
            raise ValueError(f"Invalid self.ac.emissions_grid_source {self.ac.emissions_grid_source}")

        if self.ac.emissions_grid_range == GRID_RANGE.HIGH:
            result.loc[:, "World"] = grid.loc[:, "high"].values
        elif self.ac.emissions_grid_range == GRID_RANGE.LOW:
            result.loc[:, "World"] = grid.loc[:, "low"].values
        elif self.ac.emissions_grid_range == GRID_RANGE.MEAN:
            result.loc[:, "World"] = grid.loc[:, "medium"].values
        else:
            raise ValueError(f"Invalid ac.emissions_grid_range {self.ac.emissions_grid_range}")

        # Generation mixes from the AMPERE/MESSAGE WG3 BAU scenario, direct and
        # indirect emission factors by fuel from the IPCC WG3 Annex III Table A.III.2
        # https://www.ipcc.ch/pdf/assessment-report/ar5/wg3/ipcc_wg3_ar5_annex-iii.pdf
        result.loc[:, "OECD90"] = 0.454068989
        result.loc[:, "Eastern Europe"] = 0.724747956
        result.loc[:, "Asia (Sans Japan)"] = 0.457658947
        result.loc[:, "Middle East and Africa"] = 0.282243907
        result.loc[:, "Latin America"] = 0.564394712
        result.loc[:, "China"] = 0.535962403
        result.loc[:, "India"] = 0.787832379
        result.loc[:, "EU"] = 0.360629290
        result.loc[:, "USA"] = 0.665071666
        return result


    @lru_cache()
    @data_func
    def conv_ref_grid_CO2_per_KWh(self):
        """Generation mixes from the AMPERE/MESSAGE WG3 BAU scenario, direct emission
           factors by fuel from the IPCC WG3 Annex III Table A.III.2.
           "Emissions Factors"!A66:K112
        """
        result = pd.DataFrame(index=list(range(2015, 2061)),
                              columns=["World", "OECD90", "Eastern Europe", "Asia (Sans Japan)",
                                       "Middle East and Africa", "Latin America", "China", "India",
                                       "EU", "USA"])
        result.index.name = "Year"
        result.loc[:, "World"] = 0.484512031078339
        result.loc[:, "OECD90"] = 0.392126590013504
        result.loc[:, "Eastern Europe"] = 0.659977316856384
        result.loc[:, "Asia (Sans Japan)"] = 0.385555833578110
        result.loc[:, "Middle East and Africa"] = 0.185499981045723
        result.loc[:, "Latin America"] = 0.491537630558014
        result.loc[:, "China"] = 0.474730312824249
        result.loc[:, "India"] = 0.725081980228424
        result.loc[:, "EU"] = 0.297016531229019
        result.loc[:, "USA"] = 0.594563066959381
        return result


# "Emissions Factors"!A290:D336
_world_meta_1 = pd.DataFrame([
    [2015, 0.580491641, 0.726805942, 0.444419682], [2016, 0.580381730, 0.726494196, 0.444511607],
    [2017, 0.580191808, 0.726117383, 0.444508574], [2018, 0.579932742, 0.725684840, 0.444422987],
    [2019, 0.579613986, 0.725204693, 0.444265621], [2020, 0.581083120, 0.726403172, 0.446005409],
    [2021, 0.578829123, 0.724128766, 0.443771822], [2022, 0.578376324, 0.723544325, 0.443450666],
    [2023, 0.577890875, 0.722935374, 0.443088717], [2024, 0.577377675, 0.722306095, 0.442691597],
    [2025, 0.576724036, 0.721565698, 0.442124716], [2026, 0.576284921, 0.721000946, 0.441811237],
    [2027, 0.575712661, 0.720331282, 0.441336382], [2028, 0.575127412, 0.719653850, 0.440843316],
    [2029, 0.574531990, 0.718971040, 0.440335281], [2030, 0.573264022, 0.717635960, 0.439134425],
    [2031, 0.573320545, 0.717597727, 0.439285704], [2032, 0.572708901, 0.716910953, 0.438749190],
    [2033, 0.572095895, 0.716226301, 0.438207831], [2034, 0.571483259, 0.715545242, 0.437663617],
    [2035, 0.570821497, 0.714820866, 0.437064470], [2036, 0.570265395, 0.714199285, 0.436573847],
    [2037, 0.569663069, 0.713536875, 0.436031604], [2038, 0.569066909, 0.712883028, 0.435493132],
    [2039, 0.568478136, 0.712238796, 0.434959817], [2040, 0.567083308, 0.710887186, 0.433521771],
    [2041, 0.567327331, 0.710983152, 0.433913852], [2042, 0.566767481, 0.710373641, 0.433403663],
    [2043, 0.566219394, 0.709777559, 0.432903570], [2044, 0.565684079, 0.709195799, 0.432414701],
    [2045, 0.565044176, 0.708501694, 0.431829000], [2046, 0.564655700, 0.708078732, 0.431475009],
    [2047, 0.564164556, 0.707545143, 0.431026311], [2048, 0.563690051, 0.707029331, 0.430593113],
    [2049, 0.563233144, 0.706532169, 0.430176460], [2050, 0.563942003, 0.707108074, 0.431018275],
    [2051, 0.562376012, 0.705597348, 0.429397017], [2052, 0.561977781, 0.705161518, 0.429036385],
    [2053, 0.561601149, 0.704748013, 0.428696627], [2054, 0.561247194, 0.704357833, 0.428378896],
    [2055, 0.560917031, 0.703992021, 0.428084382], [2056, 0.560611819, 0.703651663, 0.427814318],
    [2057, 0.560332776, 0.703337903, 0.427569991], [2058, 0.560081211, 0.703051332, 0.427353431],
    [2059, 0.559858464, 0.702793863, 0.427165406], [2060, 0.559324305, 0.702254712, 0.426636240]],
    columns=['Year', 'medium', 'high', 'low'])

# "Emissions Factors"!F290:I336
_world_ipcc = pd.DataFrame([
    [2015, 0.484233479886851, 0.954301230978324, 0.415714611547194],
    [2016, 0.483874688367180, 0.953705808726241, 0.415699168023559],
    [2017, 0.483468578344429, 0.953091499730308, 0.415616211090683],
    [2018, 0.483022233781448, 0.952462141044895, 0.415474739683663],
    [2019, 0.482541827613129, 0.951821094094534, 0.415282575858891],
    [2020, 0.483415642278809, 0.952177536197487, 0.416520905499686],
    [2021, 0.481499412617218, 0.950514955984204, 0.414772457309720],
    [2022, 0.480945957200632, 0.949854330000227, 0.414465552432322],
    [2023, 0.480375890793439, 0.949191227373746, 0.414130387202149],
    [2024, 0.479792370097929, 0.948527306071946, 0.413771028606294],
    [2025, 0.479129875365096, 0.947838144272479, 0.413292094853295],
    [2026, 0.478595824341775, 0.947202675323842, 0.412993759718887],
    [2027, 0.477987474489965, 0.946544387335615, 0.412581910201081],
    [2028, 0.477375134675864, 0.945890189693049, 0.412158128728530],
    [2029, 0.476760604919920, 0.945241007845619, 0.411724756299051],
    [2030, 0.475609144710954, 0.944163265130839, 0.410760518917611],
    [2031, 0.475531330098496, 0.943960978462593, 0.410837481063205],
    [2032, 0.474919397316536, 0.943331597296287, 0.410387213255880],
    [2033, 0.474310925799146, 0.942710164328208, 0.409934674540315],
    [2034, 0.473707024060823, 0.942097253091754, 0.409481302620380],
    [2035, 0.473069619537973, 0.941464119365002, 0.408987650013088],
    [2036, 0.472516992530166, 0.940899134962305, 0.408577287386756],
    [2037, 0.471932749289687, 0.940314944696740, 0.408129046349254],
    [2038, 0.471356840757086, 0.939741296080086, 0.407684776056632],
    [2039, 0.470790067978465, 0.939178632698648, 0.407245483451931],
    [2040, 0.469678044528875, 0.938292812842989, 0.406144087639722],
    [2041, 0.469686967218630, 0.938087976021352, 0.406385614113651],
    [2042, 0.469152097173049, 0.937560823287853, 0.405966833587310],
    [2043, 0.468629288818192, 0.937046343521181, 0.405556634681864],
    [2044, 0.468119232533872, 0.936544954506346, 0.405155846275011],
    [2045, 0.467511263814817, 0.935948980928557, 0.404676293987320],
    [2046, 0.467140086966888, 0.935583127327976, 0.404385713672719],
    [2047, 0.466672338575004, 0.935123538476659, 0.404017937790258],
    [2048, 0.466220041675584, 0.934678754794794, 0.403662724592571],
    [2049, 0.465783884392082, 0.934249237215735, 0.403320851377671],
    [2050, 0.466202378014719, 0.934415166260444, 0.403919169849744],
    [2051, 0.464962806154690, 0.933437918543026, 0.402680273560695],
    [2052, 0.464579339264012, 0.933057121808404, 0.402383178115162],
    [2053, 0.464214935271267, 0.932693614309824, 0.402102653404484],
    [2054, 0.463870395799940, 0.932347969864178, 0.401839564471306],
    [2055, 0.463546558438388, 0.932020795519145, 0.401594806949223],
    [2056, 0.463244298699963, 0.931712733709783, 0.401369308350724],
    [2057, 0.462964541559962, 0.931424469977991, 0.401164041108521],
    [2058, 0.462707434123228, 0.931155096821641, 0.400980275898344],
    [2059, 0.462474856382921, 0.930907038457189, 0.400818857404330],
    [2060, 0.462020537057214, 0.930512636676233, 0.400404559244924]],
    columns=['Year', 'medium', 'high', 'low'])

# "Emissions Factors"!A290:D336 in the 2020 version of the Excel files.
_world_meta_2 = pd.DataFrame([
    [2015, 0.619753649484954, 0.834200994227942, 0.446911398737087],
    [2016, 0.613223327855322, 0.827419241197181, 0.441324423346894],
    [2017, 0.606715005275064, 0.817903147977287, 0.436594799095373],
    [2018, 0.602650482222055, 0.811957311805342, 0.433711588716669],
    [2019, 0.599546311600711, 0.808809196292089, 0.431043861809484],
    [2020, 0.595844101320605, 0.805066315637190, 0.427859783304937],
    [2021, 0.592313613174105, 0.801495614192573, 0.424823161474647],
    [2022, 0.588839905934230, 0.797975220897886, 0.421832598087871],
    [2023, 0.585449295836798, 0.794534135403531, 0.418911809360421],
    [2024, 0.582134106340607, 0.791164960038795, 0.416054306144423],
    [2025, 0.579212349557159, 0.788184425039760, 0.413534464382670],
    [2026, 0.575701698847632, 0.784615063765847, 0.410505236766206],
    [2027, 0.572571412159762, 0.781421736177582, 0.407802618493011],
    [2028, 0.569490331287843, 0.778275031115247, 0.405141116198009],
    [2029, 0.566452830841887, 0.775169515850856, 0.402515970114720],
    [2030, 0.563582610910188, 0.772224408553539, 0.400032800926231],
    [2031, 0.560487575191628, 0.769061765323778, 0.397356976482730],
    [2032, 0.557549996015452, 0.766050030587511, 0.394814811934275],
    [2033, 0.554636302401122, 0.763060441667938, 0.392292329996334],
    [2034, 0.551742154484868, 0.760088796218024, 0.389785854191242],
    [2035, 0.548784376564443, 0.757051944289887, 0.387224226526241],
    [2036, 0.545979252104998, 0.754165935635464, 0.384793649089973],
    [2037, 0.543106698312767, 0.751211316808699, 0.382304463418555],
    [2038, 0.540236787794954, 0.748258161570859, 0.379817005842378],
    [2039, 0.537352597396159, 0.745289123477943, 0.377317616531354],
    [2040, 0.534257808148527, 0.742113543256056, 0.374637411133684],
    [2041, 0.531581023073820, 0.739345510659962, 0.372313849192314],
    [2042, 0.528685258247064, 0.736362655581270, 0.369802465048003],
    [2043, 0.525775521926616, 0.733365101778856, 0.367278694303595],
    [2044, 0.522848765756972, 0.730349877395092, 0.364739945323485],
    [2045, 0.519796747547837, 0.727206616166885, 0.362092302098936],
    [2046, 0.516932341500910, 0.724254851488976, 0.359607432066743],
    [2047, 0.513936894157109, 0.721169405528371, 0.357008750494339],
    [2048, 0.510912853777991, 0.718054985950131, 0.354385243670808],
    [2049, 0.508316537396635, 0.715381773638989, 0.352134907312678],
    [2050, 0.506594921787481, 0.713622488394168, 0.350653654650227],
    [2051, 0.504688929275709, 0.711690195955989, 0.349010631116045],
    [2052, 0.502854324722711, 0.709827677277282, 0.347428887775673],
    [2053, 0.500981466874364, 0.707928699401097, 0.345814547929372],
    [2054, 0.499068430228993, 0.705991414176679, 0.344165978406253],
    [2055, 0.497072403296562, 0.703969699319331, 0.342445358912229],
    [2056, 0.495114656946048, 0.701995050774066, 0.340760075761759],
    [2057, 0.493070596435275, 0.699932787017676, 0.338999924825479],
    [2058, 0.490979702541600, 0.697825838098367, 0.337199902765339],
    [2059, 0.488840556318235, 0.695672846558836, 0.335358807437345],
    [2060, 0.486810301162345, 0.693612676011530, 0.333607332510495]],
    columns=['Year', 'medium', 'high', 'low'])

# Variant "Emissions Factors"!A290:D336 in solutions like Bike Infrastructure
# in the Drawdown 2020 edition.
_world_meta_3 = pd.DataFrame([
    [2015, 0.617381627523255, 0.830817877069664, 0.446511800066534],
    [2016, 0.613053711917674, 0.824698901512021, 0.443404400078671],
    [2017, 0.605559021113794, 0.815532512015463, 0.437490678056033],
    [2018, 0.599823764037522, 0.807926586189615, 0.433230012701179],
    [2019, 0.596692109138654, 0.804739279793431, 0.430557603413934],
    [2020, 0.592956465174414, 0.800948724769081, 0.427367828954101],
    [2021, 0.589394210498330, 0.797332726214472, 0.424325795194590],
    [2022, 0.585889940804312, 0.793768752747037, 0.421330025011830],
    [2023, 0.582469966488571, 0.790285795690257, 0.418404233626765],
    [2024, 0.579126508336472, 0.786876310967440, 0.415541914399482],
    [2025, 0.576180723793771, 0.783861513867133, 0.413017979130062],
    [2026, 0.572640473126760, 0.780249944881284, 0.409983708694097],
    [2027, 0.569484653817574, 0.777020209351351, 0.407276740536253],
    [2028, 0.566378787697806, 0.773838162055771, 0.404611015683456],
    [2029, 0.563317175272247, 0.770698264597087, 0.401981761744236],
    [2030, 0.560425096459919, 0.767721987885512, 0.399494868550752],
    [2031, 0.557305440093151, 0.764524237131432, 0.396814849591601],
    [2032, 0.554345365121137, 0.761480424779140, 0.394268852529604],
    [2033, 0.551409591841439, 0.758459351619903, 0.391742608972507],
    [2034, 0.548493724307989, 0.755456735336789, 0.389232432888142],
    [2035, 0.545513743488868, 0.752388223445871, 0.386667022609245],
    [2036, 0.542688055628436, 0.749472892651180, 0.384232941873367],
    [2037, 0.539794403434954, 0.746488188806800, 0.381740161756609],
    [2038, 0.536903541206374, 0.743505157722919, 0.379249134726127],
    [2039, 0.533998346916998, 0.740506169378769, 0.376746167071146],
    [2040, 0.530880184208068, 0.737297260044097, 0.374061979635782],
    [2041, 0.528185054593160, 0.734503069266229, 0.371735292412725],
    [2042, 0.525268472346747, 0.731490529832329, 0.369220361692718],
    [2043, 0.522337858549740, 0.728463206037271, 0.366693034140975],
    [2044, 0.519390127508675, 0.725418072781803, 0.364150711760779],
    [2045, 0.516316182594658, 0.722243545426141, 0.361499332976304],
    [2046, 0.513431317163278, 0.719262606929121, 0.359010977365359],
    [2047, 0.510414388803142, 0.716146530365413, 0.356408636163102],
    [2048, 0.507368630222783, 0.713001141973038, 0.353781429301529],
    [2049, 0.504753471538005, 0.710301061700499, 0.351527882859898],
    [2050, 0.503017662563427, 0.708521537592850, 0.350044212133840],
    [2051, 0.501095097574196, 0.706565613824964, 0.348398365216802],
    [2052, 0.499244741360773, 0.704680634250964, 0.346813938332699],
    [2053, 0.497355610112209, 0.702758451510754, 0.345196826056066],
    [2054, 0.495425752440293, 0.700797180540976, 0.343545390805835],
    [2055, 0.493412239186826, 0.698750531269397, 0.341821792241291],
    [2056, 0.491436597471548, 0.696750365038799, 0.340133460333253],
    [2057, 0.489373931181422, 0.694661570589733, 0.338370139609077],
    [2058, 0.487263793557604, 0.692527181299305, 0.336566839076065],
    [2059, 0.485104746166210, 0.690345811922819, 0.334722353270288],
    [2060, 0.483057064536976, 0.688260792300398, 0.332967909468916]],
    columns=['Year', 'medium', 'high', 'low'])

# used in Drawdown 2020 Alternative Cement
_world_meta_4 = pd.DataFrame([
    [2015, 0.619731238862595, 0.833329897638502, 0.447394567903417],
    [2016, 0.613191401904823, 0.826475738292122, 0.441840091403282],
    [2017, 0.606673460423821, 0.816888151363190, 0.437142332630907],
    [2018, 0.602621620826105, 0.810921431890408, 0.434283943572488],
    [2019, 0.599517169584422, 0.807763244481335, 0.431621781691129],
    [2020, 0.595814617939265, 0.804008111709454, 0.428444472850274],
    [2021, 0.592283805449719, 0.800425769093762, 0.425414283117659],
    [2022, 0.588809786160664, 0.796894175873816, 0.422429908026953],
    [2023, 0.585418876248296, 0.793442329560030, 0.419515064976376],
    [2024, 0.582103398123095, 0.790062794855959, 0.416663285607405],
    [2025, 0.579181396011097, 0.787073454637732, 0.414148308994488],
    [2026, 0.575670443079687, 0.783493246155346, 0.411125074787444],
    [2027, 0.572539895698304, 0.780290561875727, 0.408427626368065],
    [2028, 0.569458561763715, 0.777134774004723, 0.405771142598445],
    [2029, 0.566420815129301, 0.774020422657726, 0.403150878716958],
    [2030, 0.563550372013766, 0.771067304949067, 0.400672135522024],
    [2031, 0.560455084913133, 0.767895639229866, 0.398001296275715],
    [2032, 0.557517276050081, 0.764875660678135, 0.395463686683625],
    [2033, 0.554603356997654, 0.761877980438385, 0.392945675443809],
    [2034, 0.551708987319473, 0.758898375611644, 0.390443597434166],
    [2035, 0.548750982702714, 0.755853387203211, 0.387886465419616],
    [2036, 0.545945648286556, 0.752959842879268, 0.385460051667747],
    [2037, 0.543072879075145, 0.749997492326640, 0.382975138007765],
    [2038, 0.540202754635895, 0.747036659119172, 0.380491922741082],
    [2039, 0.537318349782893, 0.744059923934800, 0.377996786304940],
    [2040, 0.534223321887233, 0.740875778267926, 0.375321313573634],
    [2041, 0.531546349510856, 0.738101023126640, 0.373001466040980],
    [2042, 0.528650372133802, 0.735110539290677, 0.370494297014854],
    [2043, 0.525740422649863, 0.732105334722523, 0.367974753548975],
    [2044, 0.522813452322305, 0.729082423881671, 0.365440251567938],
    [2045, 0.519761210236833, 0.725931127387228, 0.362797048070022],
    [2046, 0.516896595295224, 0.722971865157726, 0.360316320660926],
    [2047, 0.513900928625662, 0.719878547258031, 0.357721988571989],
    [2048, 0.510876666499075, 0.716756168821856, 0.355102879257204],
    [2049, 0.508280157733779, 0.714076051555076, 0.352856358095056],
    [2050, 0.506558397207335, 0.712311565005700, 0.351377979310044],
    [2051, 0.504652235487031, 0.710373199412923, 0.349738311376714],
    [2052, 0.502817470106218, 0.708504908376451, 0.348159757437882],
    [2053, 0.500944446102982, 0.706599966945595, 0.346548712635171],
    [2054, 0.499031237711340, 0.704656517483214, 0.344903549039207],
    [2055, 0.497035032239839, 0.702628394583901, 0.343186470181391],
    [2056, 0.495077103173832, 0.700647188098395, 0.341504810490442],
    [2057, 0.493032852694081, 0.698578106063043, 0.339748426858670],
    [2058, 0.490941762317814, 0.696464105081149, 0.337952301275530],
    [2059, 0.488802412899276, 0.694303820554168, 0.336115235542782],
    [2060, 0.486771979815374, 0.692237263896700, 0.334367289134159]],
    columns=['Year', 'medium', 'high', 'low'])
