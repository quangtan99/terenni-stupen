import arcpy
import numpy as np



adr_1 = arcpy.GetParameterAsText(0)                                   # location of original database:"file"
adr_2 = arcpy.GetParameterAsText(1)                                   # location to save shape_file and "GeodatabASE_QT":"folder"#DMR5=adr_1+"\DMR5_zbraslav"
name_stupen = arcpy.GetParameterAsText(2)
name_DMR5 = arcpy.GetParameterAsText(3)
stupen=adr_1+"\\" + name_stupen
DMR5=adr_1+"\\"+name_DMR5
arcpy.env.overwriteOutput = True
arcpy.env.workspace =adr_1
arcpy.env.outputCoordinateSystem = arcpy.SpatialReference("WGS 1984 UTM Zone 33N")
if arcpy.Exists(DMR5) and arcpy.Exists(stupen):
   arcpy.management.CreateFolder(adr_2, "Shape_file")
   arcpy.FeatureClassToShapefile_conversion([DMR5, stupen],
                                            adr_2+"\Shape_file")
   DMR5 = adr_2+"\Shape_file" + "\\" + name_DMR5 +r".shp"
   stupen = adr_2+"\Shape_file" + "\\" + name_stupen +r".shp"
else:
   DMR5 = adr_1+"\\"+name_DMR5
   stupen = adr_1+"\\" + name_stupen
arcpy.CreateFileGDB_management(adr_2,"GeodatabASE_QT.gbd")  # create geodatabazi
arcpy.env.workspace = adr_2+"\GeodatabASE_QT.gdb"            # create workspace
arcpy.env.outputCoordinateSystem = arcpy.SpatialReference("WGS 1984 UTM Zone 33N")
arcpy.CopyFeatures_management(stupen, "stupen")

def change_value( layer, field):                                       # funkce to convert shape_length into natural number 1-n
    previousValue = 0.0
    with arcpy.da.UpdateCursor(layer, field) as cursor:
        k = 0
        for row in cursor:
            if row[0] != previousValue:
                k = k + 1.0
                previousValue = row[0]
                row[0] = k
                cursor.updateRow(row)
            else:
                row[0] = k
                cursor.updateRow(row)
def assign(list_1,list_2, layer, field):                                # assign values of this list to other list
    with arcpy.da.UpdateCursor(layer, field) as cursor:
        for row in cursor:
            list_1.append(row)
    list_2.append(list_1)
    print(list_2)
def delete_row(layer, field):                                           # delete rows having same values in layer that is next to each others
    previousValue = 0.0
    with arcpy.da.UpdateCursor(layer, field) as cursor:
        for row in cursor:
            if row[0] != previousValue:
                previousValue = row[0]
            else:
                cursor.deleteRow()
def change_value_1_to_n(layer, field):                                  # assign 1 to n just like index to use for based field when using summary statistics
    previousValue = 1
    with arcpy.da.UpdateCursor(layer, field) as cursor:
        for row in cursor:
            row[0] = previousValue
            previousValue = previousValue + 1
            cursor.updateRow(row)
from arcpy.sa import *

# interpolation of input data and output is a layer of grid.
# cell size is 1 meter
out_raster = NaturalNeighbor(DMR5, "Shape.Z", 1)
out_raster.save(r"memory\out_raster")
print("create GRID")

# create surface of curvature.
out_Curvature = SurfaceParameters(r"memory\out_raster", "PROFILE_CURVATURE",
                                  "BIQUADRATIC", "1 METERS","ADAPTIVE_NEIGHBORHOOD")
out_Curvature.save(r"memory\curvature")
print("curvature")
#create surface of slope.
out_slope = SurfaceParameters(r"memory\out_raster", "SLOPE", "BIQUADRATIC",
                              "1 METER","ADAPTIVE_NEIGHBORHOOD","METER","DEGREE")
out_slope.save(r"memory\slope_1")
print("slope")

#create surface of slope change.
# that means: slope once again as druha derivace.
out_Slope2 = Slope(r"memory\slope_1","DEGREE",1,method="PLANAR")
out_Slope2.save(r"memory\slope_2")
print("slope of slope")

# reclassify values of curvature.
# values in inteval [-4,0] are assigned by -1 and [0,4] are assigned by 1.
out_reclassify_1= Reclassify(r"memory\curvature","Value",RemapRange([[-4,0,-1],[0,4,1]]),"NODATA")
out_reclassify_1.save(r"memory\Re_curva_1")
print("reclassify curvature")

# reclassify values of slope change.
# values in inteval [0,50] are assigned by -1 and [50,90] are assigned by 1.
out_reclassify_1 = Reclassify(r"memory\slope_2","Value",RemapRange([[0,50,-1],[50,90,1]]),"NODATA")
out_reclassify_1.save(r"memory\Re_slope_2")
print("reclassify slope of slope")

# extract by attribute.
# we extract reclassifying values 1.
# that means: we take values of curvature greater than 0 and values of slope change greater than 50.
attExtract = ExtractByAttributes(r"memory\re_curva_1","VALUE=-1")
attExtract.save(r"memory\attextract1")
attExtract = ExtractByAttributes(r"memory\re_slope_2","VALUE=1")
attExtract.save(r"memory\attextract2")
print("extractions")

# combine two previous extracted layers.
# that means: pixels which locate in the same position in two layers will be kept and others will be removed.
print("combine of slope_2 extracted and curvature extracted")
outCombine = Combine([r"memory\attextract1", r"memory\attextract2",])
outCombine.save(r"memory\combine")
print("combine")

# convert layer in form of raster into polygon.
arcpy.RasterToPolygon_conversion(r"memory\combine", "polygon1","NO_SIMPLIFY","Value","SINGLE_OUTER_PART")
print("raster to polygon")


#eliminate polygons in area smaller than 10 square meters.
male_polygony=arcpy.SelectLayerByAttribute_management("polygon1","NEW_SELECTION",'"shape_Area"<10')
arcpy.MultipartToSinglepart_management(male_polygony, r"memory\multi_single")
arcpy.Erase_analysis("polygon1",r"memory\multi_single",r"memory\Erase")
print("polygons without ones smaller than 10m2")

# convert back layer in form of polygon into raster.
arcpy.PolygonToRaster_conversion(r"memory\Erase", "gridcode",r"memory\polygon_raster",
                                 "MAXIMUM_COMBINED_AREA", cellsize= 1)
print("polygon to raster")
arcpy.Delete_management("polygon1")
# vectorization for previous raster layer.
# that means: Ze všech pixelů tvořících šířku linie jsou vybrány ty, které jsou v jejím středu a přitom
# průběh linie zůstává spojitý( "thin" tool was called).
# and then: Od počátečního ke koncovému pixelu jsou jednotlivé pixely spojovány do jedné linie ("raster to polyline" tool was called)
# after that, we can observe bottom egde of terrain steps.
thinOut = Thin(r"memory\polygon_raster","NODATA", "NO_FILTER", "ROUND", 5)
thinOut.save(r"memory\thin")
print("thin")
arcpy.RasterToPolyline_conversion(r"memory\thin", r"memory\raster_polyline", "ZERO", 10, "SIMPLIFY")
print("raster to polyline")

spatial_ref = arcpy.Describe(stupen).spatialReference

# generate points along lines for upper edges with distance 10 meters.
arcpy.GeneratePointsAlongLines_management("stupen",
                                          r"memory\point_along_lines", "DISTANCE", Distance="10 meters", Include_End_Points='END_POINTS')
print("generate points along lines for upper edges by distance 10 m")

# split upper edges at created points.
# that means: each splited segment has a length of 10 meters.
arcpy.SplitLineAtPoint_management("stupen",
                                  r"memory\point_along_lines",r"memory\split_line_at_points", "0.2 meters")
print("split lines at points")

# sort segments of each upper steps in ascending order for further use.
arcpy.Sort_management(r"memory\split_line_at_points",r"memory\split_line_at_points_sorted_1" ,[["ORIG_FID","ASCENDING"],["ORIG_SEQ","ASCENDING"]])

# use created functions to edit database so that we can easily analyse and handle algorithms later.
# !!!-- these punctions won't change the main information of data in database. --!!!
change_value(r"memory\split_line_at_points_sorted_1", "Shape_Leng")
change_value_1_to_n(r"memory\split_line_at_points_sorted_1", "ORIG_FID")


# target: calculate average altitude of created segments.
# at first, we generate points along segments with interval of 5 meters.
# then we extract altitude values to created points.
# after that, we use statistic to calculate average altitude values of each segment.
arcpy.GeneratePointsAlongLines_management(r"memory\split_line_at_points_sorted_1", r"memory\point_along_lines_5m", "DISTANCE",
                                          Distance="5 meters",Include_End_Points='END_POINTS')
print("generate points along lines for upper edges by distance 5 m")
ExtractValuesToPoints(r"memory\point_along_lines_5m", r"memory\out_raster", r"memory\values_to_points_5m")
delete_row(r"memory\values_to_points_5m", "RASTERVALU")
arcpy.Statistics_analysis(r"memory\values_to_points_5m", r"memory\summary_5m", [["RASTERVALU", "MEAN"],["ORIG_FID", "MEAN"]], ["Shape_Leng", "ORIG_SEQ"])
arcpy.JoinField_management(r"memory\split_line_at_points_sorted_1", "ORIG_FID", r"memory\summary_5m", "MEAN_ORIG_FID", ["MEAN_RASTERVALU"])
with arcpy.da.UpdateCursor(r"memory\split_line_at_points_sorted_1", "MEAN_RASTERVALU") as cursor:
    for row in cursor:
        if row[0]==None:
            cursor.deleteRow()



# generate points along lines for bottom edges.
# bottom edges mean the lines we found after proces of vectorization.
arcpy.GeneratePointsAlongLines_management(r"memory\raster_polyline",r"memory\point_along_lines_dolnihrany",
                                          "DISTANCE", Distance="2 meters", Include_End_Points='END_POINTS')
print("generate points along lines")

# extract altitude values to generated points.
ExtractValuesToPoints(r"memory\point_along_lines_dolnihrany",r"memory\out_raster",r"memory\values_to_points_dolni_for_5m")
print("extract values to points")


# count how many devided segments with length 10 meters are.
# assign results to variable "number_row_split".
number_row_split=int(str(arcpy.management.GetCount(r"memory\split_line_at_points_sorted_1")))
print("number_row_split= ",number_row_split)


arcpy.Statistics_analysis(r"memory\split_line_at_points_sorted_1",r"memory\summary", [["ORIG_FID", "SUM"]], "Shape_Leng")
                # assign that amount of small lines of each step to a list ORIG_FID0 to use it later
                # this process is just like to assign index of the upper steps
ORIG_FID0 = []
with arcpy.da.UpdateCursor(r"memory\summary", "FREQUENCY") as cursor:
    for row in cursor:
        ORIG_FID0.append(row)
print(ORIG_FID0)
arcpy.Delete_management(r"memory\summary")
                # convert Shapeleng of steps into number from 1 to n
change_value("stupen", "Shape_Leng")
                # declaring some lists
ORIG_FID5 = []
ORIG_FID6 = []
skok=[]                                              # "skok" was used to count the number of times of each steps not covering any points in bottom edges
fre = []                                             # and "fre" was used to count the number of times of each steps covering any points in bottom edges
index = []
for i in range(0,int(str(arcpy.management.GetCount("stupen")))):
    skok.append(0)
    fre.append(0)
ORIG_SEQ=[]                                          #ORIG_SEQ is a list to use for storing indexes of the short lines, those ralative heghts are lower than 2m
ORIG_SEQ_2=[]                                        #ORIG_SEQ_2 is a list to use for storing the short lines, those ralative heghts are taller than 2m
ORIG_SEQ_rozdil=[]                                   #ORIG_SEQ_rozdil is a list to use for storing rozdil of the short lines, those ralative heghts are lower than 2m
index_kazdeho_useku=[]
vyska_kazdeho_useku=[]
find_outliners=[]
pocet_outliners=[]
for i in range(0,int(str(arcpy.management.GetCount("stupen")))):
    ORIG_SEQ.append([])
    ORIG_SEQ_rozdil.append([])
    ORIG_SEQ_2.append([])
    index_kazdeho_useku.append([])
    vyska_kazdeho_useku.append([])
    find_outliners.append([])
    pocet_outliners.append([])

with arcpy.da.UpdateCursor("stupen", "Shape_leng") as cursor:           # assign length of tarrain step to a list "index"
    for row in cursor:
        index.append(row)
t=2                                                 # "t" is distance of each time using buffer in "while loop" below
i = t
limit= 3                                            # use "limit" so that process is able to stop if any small line of upper step doesnt cover any point when using buffer
while number_row_split > limit:                     #this "while" loop uses for find points of bottom steps corresponding to each short lines of upper steps
    print("distance=", i )
                                                    # use condition "if-else" here because with 1. buffer we use " split line at point"
                                                    # but then after the first loop, we use the previous intersect: "intersect + str(i-t)"
    if i==t:
        arcpy.Buffer_analysis(r"memory\split_line_at_points_sorted_1",                   # buffer by distance "t"
                              r"memory\buffer", str(i) + " meters", "RIGHT","FLAT","","","GEODESIC" )
    else:
        arcpy.Buffer_analysis(r"memory\intersect"+str(i-t),r"memory\buffer", str(i) + " meters", "RIGHT","FLAT","","","GEODESIC" )      # buffer by distance "t"

    arcpy.Intersect_analysis([r"memory\buffer",r"memory\values_to_points_dolni_for_5m"],r"memory\intersect", "ALL")                             # intersect of buffer and points in bottom steps
    arcpy.Statistics_analysis(r"memory\intersect", r"memory\summary_rozdil",
                              [["RASTERVALU", "MEAN"], ["MEAN_RASTERVALU", "MEAN"]],
                              ["Shape_Leng", "ORIG_SEQ"])           # average heights of points of bottom steps corresponding to each......
    arcpy.AddField_management(r"memory\summary_rozdil", "rozdil", "DOUBLE", 13, "", "", "rozdil",
                              "NULLABLE", "REQUIRED")                   # add a field "rozdil" expressing the ralative heights of each short lines of upper
    arcpy.management.CalculateField(r"memory\summary_rozdil", "rozdil", "!MEAN_MEAN_RASTERVALU!-!MEAN_RASTERVALU!", "PYTHON3")  # caculate the "rozdil"
    with arcpy.da.UpdateCursor(r"memory\summary_rozdil", ["Shape_Leng", "ORIG_SEQ", "rozdil"]) as cursor:      # assign rozdil<2 to ORIG_SEQ
        for row in cursor:
            index_kazdeho_useku[int(row[0]) - 1].append((row[1]))
            vyska_kazdeho_useku[int(row[0]) - 1].append(row[2])
            find_outliners[int(row[0]) - 1].append(i)
            if row[2] < 2:
                ORIG_SEQ[int(row[0]) - 1].append(int(row[1]))
                ORIG_SEQ_rozdil[int(row[0]) - 1].append(row[2])
            else:
                ORIG_SEQ_2[int(row[0]) - 1].append(row[2])
    print(index_kazdeho_useku)
    print(find_outliners)
    print(ORIG_SEQ)
    print(ORIG_SEQ_rozdil)
    print(ORIG_SEQ_2)
    number_row_intersect = int(str(arcpy.management.GetCount(r"memory\intersect")))
    print("number_row_intersect_BEFORE=", number_row_intersect)
    arcpy.DeleteIdentical_management(r"memory\intersect", "ORIG_FID")
    number_row_intersect = int(str(arcpy.management.GetCount(r"memory\intersect")))
    print("number_row_intersect_AFTER=",number_row_intersect)
                # if intersect = 0 , just add an empty list to result
                # if not we use process below to add hights, frequence
    if number_row_intersect!=0:
        arcpy.Intersect_analysis([r"memory\buffer",r"memory\point_along_lines_dolnihrany"],r"memory\intersect_points", "ALL")
        ExtractValuesToPoints(r"memory\intersect_points",r"memory\out_raster",r"memory\values_to_points")
        arcpy.Statistics_analysis(r"memory\values_to_points",r"memory\summary", [["RASTERVALU", "SUM"]], "Shape_Leng")

        arcpy.Intersect_analysis([r"memory\buffer", r"memory\raster_polyline"], r"memory\intersect_points1", "ALL")
        arcpy.DeleteIdentical_management(r"memory\intersect_points1", "ORIG_FID")
        arcpy.Statistics_analysis(r"memory\intersect_points1", r"memory\summary1", [["ORIG_FID", "SUM"]], "Shape_Leng")
                #assign statistical values to lists
        # fre[index.index(ORIG_FID5[m])]=fre[index.index(ORIG_FID5[m])]+int(''.join([str(element) for element in ORIG_FID7[m]]))
        ORIG_FID5 = []
        assign(ORIG_FID5, ORIG_FID6, r"memory\summary", "Shape_Leng")
        for m in range(0, len(skok)):
            skok[m] = skok[m]+1;
        for m in range(0,len(ORIG_FID5)):
            skok[index.index(ORIG_FID5[m])]=0;
    else:
        ORIG_FID6.append([])
        for r in range(0, len(skok)):
            skok[r] = skok[r]+1;
    print(skok)

    for k in range(0, len(skok)):                                       # to find which wrong steps are
        if skok[k] == 12 /t and len(index_kazdeho_useku[k]) / \
                int(''.join([str(element) for element in ORIG_FID0[k]])) < 0.5:
            if len(index_kazdeho_useku[k]) / int(''.join([str(element) for element in ORIG_FID0[k]]))== 0:
                continue
            else:
                limit = limit - len(index_kazdeho_useku[k]) + \
                        int(''.join([str(element) for element in ORIG_FID0[k]]))
                with arcpy.da.UpdateCursor(r"memory\intersect"+str(i-t), "Shape_Leng") as cursor:
                    for row in cursor:
                        if row[0] == float(''.join([str(element) for element in index[k]])):
                            cursor.deleteRow()
                print(limit)
        if (skok[k]==8/t and len(index_kazdeho_useku[k]) /
            int(''.join([str(element) for element in ORIG_FID0[k]]))>=0.8) \
                or(skok[k] == 10 / t and len(index_kazdeho_useku[k]) /
                   int(''.join([str(element) for element in ORIG_FID0[k]])) >= 0.65 and
                   len(index_kazdeho_useku[k]) /
                   int(''.join([str(element) for element in ORIG_FID0[k]]))<0.8) \
                or(skok[k] == 12 / t and len(index_kazdeho_useku[k]) /
                   int(''.join([str(element) for element in ORIG_FID0[k]])) >= 0.50 and
                   len(index_kazdeho_useku[k]) /
                   int(''.join([str(element) for element in ORIG_FID0[k]]))<0.65):
            limit = limit - len(index_kazdeho_useku[k])   \
                    + int(''.join([str(element) for element in ORIG_FID0[k]]))
            with arcpy.da.UpdateCursor(r"memory\intersect" + str(i - t), "Shape_Leng") as cursor:
                for row in cursor:
                    if row[0] == float(''.join([str(element) for element in index[k]])):
                        cursor.deleteRow()
            print(limit)

    select = arcpy.SelectLayerByLocation_management(r"memory\buffer","CONTAINS",r"memory\point_along_lines_dolnihrany")
    arcpy.MultipartToSinglepart_management(select, r"memory\multi_single2")
    arcpy.Erase_analysis(r"memory\buffer",r"memory\multi_single2",r"memory\Erase2")
    if i==t:
        arcpy.Intersect_analysis([r"memory\split_line_at_points_sorted_1", r"memory\Erase2"],r"memory\intersect" +str(i), "ALL")             # intersect
        arcpy.DeleteField_management(r"memory\intersect" +str(i),["OBJECTID","Shape","ORIG_FID","Shape_Leng","ORIG_SEQ","MEAN_RASTERVALU"],"KEEP_FIELDS")
    else:
        # arcpy.Intersect_analysis(["intersect"+str(i-t), "Erase2"],"intersect"+str(i), "ALL")                         # intersect
        select_1 = arcpy.SelectLayerByLocation_management(r"memory\intersect"+str(i-t), "WITHIN", r"memory\Erase2")
        arcpy.MultipartToSinglepart_management(select_1, r"memory\intersect"+str(i))
        # arcpy.DeleteField_management("intersect" + str(i), ["OBJECTID","Shape","ORIG_FID","Shape_Leng","ORIG_SEQ","MEAN_RASTERVALU"],"KEEP_FIELDS")
    number_row_split = number_row_split - number_row_intersect
    arcpy.Delete_management(r"memory\buffer")
    arcpy.Delete_management(r"memory\intersect")
    arcpy.Delete_management(r"memory\multi_single2")
    arcpy.Delete_management(r"memory\Erase2")
    arcpy.Delete_management(r"memory\intersect_points")
    arcpy.Delete_management(r"memory\intersect_points1")
    arcpy.Delete_management(r"memory\values_to_points")
    arcpy.Delete_management(r"memory\summary")
    arcpy.Delete_management(r"memory\summary1")
    arcpy.Delete_management(r"memory\summary_rozdil")
    if i!=t:
        arcpy.Delete_management(r"memory\intersect"+str(i-t))
    i = i + t
arcpy.CopyFeatures_management(r"memory\split_line_at_points_sorted_1", "Prevyseni_kazdych_useku")

# sorting index in list ORIG_SEQ[i] from small value to large value.
# this one means arranging data and has no impact to the main information of data.
for i in range(0,int(str(arcpy.management.GetCount("stupen")))):
    if ORIG_SEQ[i]==[]:
        continue
    else:
        for j in range(0,len(ORIG_SEQ[i])):
            t=ORIG_SEQ[i][j]
            ORIG_SEQ[i][j]=[]
            ORIG_SEQ[i][j].append(t)
            ORIG_SEQ[i][j].append(ORIG_SEQ_rozdil[i][j])
        ORIG_SEQ[i]=sorted(ORIG_SEQ[i])
print(ORIG_SEQ)

# sorting index in list index_kazdeho_useku[i] from small value to large value.
# this one means arranging data and has no impact to the main information of data.
print(index_kazdeho_useku)
for i in range(0,int(str(arcpy.management.GetCount("stupen")))):
    if index_kazdeho_useku[i]==[]:
        continue
    elif len(index_kazdeho_useku[i])/int(''.join([str(element) for element in ORIG_FID0[i]]))<0.5:
        index_kazdeho_useku[i] = []
        continue
    else:
        for j in range(0,len(index_kazdeho_useku[i])):
            t=index_kazdeho_useku[i][j]
            index_kazdeho_useku[i][j]=[]
            index_kazdeho_useku[i][j].append(t)
            index_kazdeho_useku[i][j].append(vyska_kazdeho_useku[i][j])
            index_kazdeho_useku[i][j].append(find_outliners[i][j])
        index_kazdeho_useku[i]=sorted(index_kazdeho_useku[i])
print(index_kazdeho_useku)

# eliminate repeat rows in database.
#this process will not change the main information.
for i in range(0,int(str(arcpy.management.GetCount("stupen")))):
    previous = 0
    if index_kazdeho_useku[i]==[]:
        continue
    else:
        end=len(index_kazdeho_useku[i])
        ss=0
        for j in range(0,len(index_kazdeho_useku[i])):
            if j==end:
                break
            else:
                if index_kazdeho_useku[i][ss][0] != previous:
                    previous = index_kazdeho_useku[i][ss][0]
                    ss=ss+1
                    continue
                else:
                    index_kazdeho_useku[i].pop(ss)
for i in range(0, len(index_kazdeho_useku)):                                # chuyen so am thanh so duong
    for j in range(0,len(index_kazdeho_useku[i])):
        if index_kazdeho_useku[i][j][1]<=0:
            index_kazdeho_useku[i][j][1] = -index_kazdeho_useku[i][j][1]
            index_kazdeho_useku[i][j][2] = -index_kazdeho_useku[i][j][2]

# process of finding outliners and eliminate them from data.
for i in range(0, int(str(arcpy.management.GetCount("stupen")))):
    data_1 = []
    for j in range(1, len(index_kazdeho_useku[i])):
            if index_kazdeho_useku[i][j][2] - index_kazdeho_useku[i][j-1][2] >= 6:
                data_1.append(j)
            elif index_kazdeho_useku[i][j][2] - index_kazdeho_useku[i][j-1][2] <= -6:
                data_1.append(-j)
    zacatek = 0
    konec = 0
    pocet_zacatek = 0
    for k in range(0, len(data_1)):
        if data_1[k] < 0:
            if zacatek == 0:
                zacatek = -data_1[k]
                pocet_zacatek = pocet_zacatek + 1
        if data_1[k] > 0:
            if zacatek != 0:
                konec = data_1[k]
                pocet_zacatek = pocet_zacatek + 1
            else:
                if pocet_zacatek == 0:
                    if i <= 4:
                        konec = data_1[k]
                        pocet_zacatek = pocet_zacatek + 1
                else:
                    zacatek = data_1[k - 1]
                    konec = data_1[k]
            for h in range(zacatek, konec):
                index_kazdeho_useku[i][h][2] = -10
                pocet_outliners[i].append(index_kazdeho_useku[i][h][1])
            zacatek = 0
            konec = 0
        if k == len(data_1) - 1 and data_1[len(data_1) - 1] < 0:
            if len(index_kazdeho_useku[i]) - 1 - abs(data_1[len(data_1) - 1]) <= 4:
                zacatek = abs(data_1[len(data_1) - 1])
                konec = len(index_kazdeho_useku[i])
                for m in range(zacatek, konec):
                    index_kazdeho_useku[i][m][2] = -10
                    pocet_outliners[i].append(index_kazdeho_useku[i][m][1])
print(index_kazdeho_useku)

cele_prevyseni = []
for i in range(0, int(str(arcpy.management.GetCount("stupen")))):
    k = 0
    t=0
    if index_kazdeho_useku[i] != []:
        for j in range(0, len(index_kazdeho_useku[i])):
            if index_kazdeho_useku[i][j][2] != -10:
                k = k + index_kazdeho_useku[i][j][1]
            else:
                t=t+1
        cele_prevyseni.append(k/(len(index_kazdeho_useku[i])-t))
    else:
        cele_prevyseni.append(0)
arcpy.AddField_management("stupen", "Relativni_vyska", "DOUBLE", 13, "", "", "Relativni_vyska",
                              "NULLABLE", "REQUIRED")
with arcpy.da.UpdateCursor("stupen", ["Shape_Leng","Relativni_vyska"]) as cursor:
    for row in cursor:
        row[1]=cele_prevyseni[int(row[0])-1]
        cursor.updateRow(row)

for i in range(0,len(pocet_outliners)):                                     #total values of each children list and their frekvence.
    if pocet_outliners[i]==[]:
        pocet_outliners[i]=[0,0]
    else:
        pocet_outliners[i]=[sum(pocet_outliners[i]),len(pocet_outliners[i])]

# calculate prevyseni kazdych useku.
arcpy.AddField_management("Prevyseni_kazdych_useku", "prevyseni", "DOUBLE", 13, "", "", "prevyseni",
                              "NULLABLE", "REQUIRED")
with arcpy.da.UpdateCursor("Prevyseni_kazdych_useku",["Shape_Leng", "ORIG_SEQ","prevyseni"]) as cursor:
    Shape_Leng=1
    j=0
    for row in cursor:
        if row[0]!= Shape_Leng:
            Shape_Leng = Shape_Leng+1
            j=0
            if index_kazdeho_useku[Shape_Leng-1] == []:
                continue
            else:
                if row[1] == index_kazdeho_useku[Shape_Leng-1][j][0]:
                    row[2]= index_kazdeho_useku[Shape_Leng-1][j][1]
                    cursor.updateRow(row)
                    if j!=len(index_kazdeho_useku[Shape_Leng-1])-1:
                        j = j + 1
                    else:
                        continue

                else:
                    continue
        else:
            if index_kazdeho_useku[Shape_Leng-1] == []:
                continue
            else:
                if row[1] == index_kazdeho_useku[Shape_Leng-1][j][0]:
                    row[2] = index_kazdeho_useku[Shape_Leng-1][j][1]
                    cursor.updateRow(row)
                    if j!=len(index_kazdeho_useku[Shape_Leng-1])-1:
                        j = j + 1
                    else:
                        continue
                else:
                    continue

# eliminate segments of upper steps with the length lower than 2 meters
# but make sure to keep upper steps being continuous
for i in range(0,int(str(arcpy.management.GetCount("stupen")))):
    previous=1
    if ORIG_SEQ[i]!=[]:
        if ORIG_SEQ[i][0][0]==1:
            for j in range(0, ORIG_FID0[i][0]):
                if len(ORIG_SEQ[i])>=previous:
                    if ORIG_SEQ[i][j][0]==previous:
                        previous =previous+1
                    else:
                        previous = previous - 1
                        print(previous)
                        break
                else:
                    previous=-1
                    print(previous)
                    break
        else:
            previous = 0
            print(previous)
        back = 0
        t = len(ORIG_SEQ[i]) - 1
        for b in range(ORIG_FID0[i][0], 0, -1):
            if t == -1:
                back = -1
            else:
                if b == ORIG_SEQ[i][t][0]:
                    t = t - 1
                else:
                    back = t
                    break
        print(back)
        if previous==-1 or back==-1:
            continue
        else:
            now=0
            for h in range(previous,back+1):
                h = h - now
                ORIG_SEQ_2[i].append(ORIG_SEQ[i][h][1])
                ORIG_SEQ[i].pop(h)
                now = now + 1
print(ORIG_SEQ)

# delete line segments in layer "split_line_at_points".
# by indexs in "ORIG_SEQ" list
with arcpy.da.UpdateCursor(r"memory\split_line_at_points_sorted_1",["Shape_Leng","ORIG_SEQ"]) as cursor:
    Shape_Leng = 0
    j=0
    for row in cursor:
        if row[0]!=Shape_Leng:
            Shape_Leng=Shape_Leng+1
            j=0
            if ORIG_SEQ[Shape_Leng-1]==[]:
                continue
            else:
                if row[1] == ORIG_SEQ[Shape_Leng - 1][j][0]:
                    j=j+1
                    cursor.deleteRow()
        else:
            if ORIG_SEQ[Shape_Leng - 1] == []:
                continue
            else:
                if j <= len(ORIG_SEQ[Shape_Leng - 1]) - 1:
                    if row[1] == ORIG_SEQ[Shape_Leng - 1][j][0]:
                        j = j + 1
                        cursor.deleteRow()
                else:
                    continue

# relative height without ones with height lower than 2 meters.
arcpy.Dissolve_management(r"memory\split_line_at_points_sorted_1","Relativni_vyska_bez_prevyseni_mensich_nez_2_m",
                          ["Shape_Leng"],"", "",
                          "DISSOLVE_LINES")
for i in range(0,int(str(arcpy.management.GetCount("stupen")))):
    if ORIG_SEQ_2[i]==[]:
        ORIG_SEQ_2[i]=None
    else:
        if len(ORIG_SEQ_2[i])-pocet_outliners[i][1] == 0:
            ORIG_SEQ_2[i] = 1000
        else:
            if (sum(ORIG_SEQ_2[i])-pocet_outliners[i][0])/(len(ORIG_SEQ_2[i])-pocet_outliners[i][1])<2:
                ORIG_SEQ_2[i]=0
            else:
                ORIG_SEQ_2[i]=(sum(ORIG_SEQ_2[i])-pocet_outliners[i][0])/(len(ORIG_SEQ_2[i])-pocet_outliners[i][1])
print(ORIG_SEQ_2)
arcpy.AddField_management("Relativni_vyska_bez_prevyseni_mensich_nez_2_m", "Relativni_vyska", "DOUBLE", 13, "", "", "Relativni_vyska",
                              "NULLABLE", "REQUIRED")
with arcpy.da.UpdateCursor("Relativni_vyska_bez_prevyseni_mensich_nez_2_m", ["Shape_Leng","Relativni_vyska"]) as cursor:
    for row in cursor:
        if len(index_kazdeho_useku[int(row[0])-1]) / int(''.join([str(element) for element in ORIG_FID0[int(row[0])-1]])) < 0.5:
            row[1]=None
            cursor.updateRow(row)
        else:
            row[1]=ORIG_SEQ_2[int(row[0])-1]
            cursor.updateRow(row)

