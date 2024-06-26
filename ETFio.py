import h5py
import numpy as np
import time

# This is to make it backward compatible with python2
try:
   input = raw_input
except NameError:
   pass




def WriteETFCatalogue(format,opt,treedata,Redshift,fieldsDict):
	####################################################################################


	#Outputing the ETF into a HDF5 file, this code will work if the data is in the ETF

	####################################################################################


        filename = opt.outfilename+ ".ETF.tree.hdf"
        print("Writing ETF catalogue to ",filename)


        hdffile = h5py.File(filename,"w")

	#Create the header
        headergroup = hdffile.create_group("Header")

	#Add the options form the config into the header
        headergroup.attrs["startSnap"] = opt.startSnap
        headergroup.attrs["endSnap"] = opt.endSnap
        headergroup.attrs["Nsnaps"] = opt.Nsnaps
        headergroup.attrs["h"] = opt.h
        headergroup.attrs["boxsize"] = opt.boxsize
        headergroup.attrs["HALOIDVAL"] = opt.HALOIDVAL
        headergroup.attrs["Munit"] = "10^10 solarmasses"
        headergroup.attrs["Lunit"] = "Mpc"
        headergroup.attrs["Vunit"] = "km/s"

	#Add to the header which file the data is from
        if(format=="VEL"):

                headergroup.attrs["VELdir"] = opt.VELdir
                headergroup.attrs["VELwalkabletreefilename"] = opt.VELwalkabletreefilename
                headergroup.attrs["WWflag"] = opt.WWflag

        elif(format=="AHF"):

                headergroup.attrs["AHFhalofilelist"] = opt.AHFhalofilelist
                headergroup.attrs["AHFtreefilelist"] = opt.AHFtreefilelist

        elif(format=="Rock"):

                headergroup.attrs["Rockfilelist"] = opt.Rockfilelist

        elif(format=="Dtrees"):

                headergroup.attrs["Dtreesfilename"] = opt.Dtreesfilename
                headergroup.attrs["Dtreesvols"] = opt.Dtreesvols
                
        #Create a snapshot group
        for snap in range(opt.startSnap,opt.endSnap+1):

                snapKey = "Snap_%03d" %snap

                isnap = snap - opt.startSnap

                snapgroup = hdffile.create_group("Snap_%03d" %(snap))

                snapgroup.attrs["Redshift"] = Redshift[isnap]

                #Put all the data in the snapshot group.
                for key in treedata[snapKey].keys():

                        if("/haloTrees/" in key):
                                datasetKey = key.replace("/haloTrees/","")
                        else:
                                datasetKey = key

                        dataset = snapgroup.create_dataset(datasetKey,data =treedata[snapKey][key])

			#Add an attribute to the dataset which gives the dataset's orginal name in the catalogue
                        if((format=="VEL") | (format=="Dtrees")):
                                dataset.attrs["origFieldName"] = fieldsDict[key]
                        else:
                                dataset.attrs["origFieldName"] = fieldsDict[key][0]

        hdffile.close()


# This is the class which contains all the simulation info
class headerOptions(object):

	def __init__(self,hdffile):

		if("Header" not in hdffile.keys()):
			raise KeyError("There is no 'Header' group in the hdffile please make sure there is one")

		#Lets check all the required keys exist
		requiredHeaders = ["startSnap","startSnap","Nsnaps","h","boxsize"]
		for key in requiredHeaders:
			if(key not in hdffile["Header"].attrs): 
				raise KeyError("There is no value for '%s' in the Header please make sure the header in the file has this" %key)

		self.startSnap = np.array(hdffile["Header"].attrs["startSnap"])	
		self.endSnap = np.array(hdffile["Header"].attrs["endSnap"])		
		self.Nsnaps = np.array(hdffile["Header"].attrs["Nsnaps"])	
		self.h = np.array(hdffile["Header"].attrs["h"])		
		self.boxsize = np.array(hdffile["Header"].attrs["boxsize"])
		self.HALOIDVAL = np.array(hdffile["Header"].attrs["HALOIDVAL"])


def LoadETFCatalogue(filename,plotOpt):

        print("Reading the ETF file",filename)
        start  = time.time()

        hdffile = h5py.File(filename,"r")

        #Lets get the simultaion info from the header
        opt = headerOptions(hdffile)

        splitSnapKey = "Snap_%03d"


        treedata = {splitSnapKey %snap:{} for snap in range(opt.startSnap,opt.endSnap+1)}


        #Lets see if the WWflag is set
        if(plotOpt.WWflag):
                requiredDatasets = ["HaloID","StartProgenitor","Progenitor","Descendant","EndDescendant","Mass","Pos","HostHaloID","Radius","WWHaloFlag"]
        else:
                requiredDatasets = ["HaloID","StartProgenitor","Progenitor","Descendant","EndDescendant","Mass","Pos","HostHaloID","Radius"]

        # Lets check if the required datasets exist in the catalogue file for every snapshot
        for snap in range(opt.startSnap,opt.endSnap+1):
                snapKey = splitSnapKey %snap

                if(snapKey not in hdffile.keys()):
                        raise KeyError("There is no '%s' group in the hdffile, either create this or ajust the startSnap and endSnap values" %snapKey)


                if("Redshift" not in hdffile[snapKey].attrs):
                        raise KeyError("There is no 'Redshift' attribute for each snapshot group, please use the 'CreateMTFCatalogue' to create the ETF catalogue")

                #Make backwards compatible with the old ETF
                if(("RootProgenitor" in hdffile[snapKey]) & ("RootDescendant" in hdffile[snapKey])):
                        requiredDatasets[1] = "RootProgenitor"
                        requiredDatasets[4] = "RootDescendant"

                for key in requiredDatasets:

                        if(key not in hdffile[snapKey]):
                                raise KeyError("The required dataset %s does not exist in the file, please make sure each snapshot group has datasets " %key + " ".join(requiredDatasets))


        # Lets find what extra datasets exist in the hdf5 file
        extraDatasets = []

        for datasetKey in hdffile[snapKey].keys():

                if(datasetKey not in requiredDatasets):
                        extraDatasets.append(datasetKey)

        #Only do this if the prompt flag is on
        if(plotOpt.promptFlag):

                datasets = extraDatasets + ["Mass","Radius",",default Mass: "]
                datasetstr =  " ".join(datasets)


                sizeDataKey = input("Please select which dataset you would like to set the size of the points from the datasets:\n" + datasetstr)
                if (sizeDataKey==""):
                        sizeDataKey="Mass"

                while(sizeDataKey not in datasets):
                        sizeDataKey = input(sizeDataKey+" is not avalible please choose from the datasets:\n" + datasetstr)
                        if (sizeDataKey==""):
                                sizeDataKey="Mass"


                if(plotOpt.plotColorBar==1):
                        datasets = extraDatasets + ["Mass","Radius",",default Radius: "]
                        datasetstr =  " ".join(datasets)

                        colDataKey = input("Please select which dataset you would like to set the colour of the points from the datasets:\n" + datasetstr)
                        if(colDataKey==""):
                                colDataKey= "Radius"

                        while(colDataKey not in datasets):
                                colDataKey = input(colDataKey+" is not avalible please choose from the datasets:\n" + datasetstr)
                                if(colDataKey==""):
                                        colDataKey= "Radius"

                else:
                        print("Setting the HostHaloID as the colour, please set plotColorBar = 1 in plot_config.cfg if you would like a different dataset to be used")
                        colDataKey= "HostHaloID"

                if((plotOpt.plotColorBar==0) & (colDataKey!="HostHaloID")):
                        raise SystemExit("If using different field from HostHaloID, please set plotColorBar = 1 in the Plot_config.cfg")



                if(plotOpt.overplotdata):
                        datasets = extraDatasets + ["HaloID","StartProgenitor","Progenitor","Descendant","EndDescendant","Mass","HostHaloID",",default HaloID: "]
                        datasetstr =  " ".join(datasets)

                        overDataKey = input("Please select which dataset which is to be overplotted form the datasets:\n" + datasetstr)
                        if(overDataKey==""):
                                overDataKey= "HaloID"

                        while(overDataKey not in datasets):
                                overDataKey = input(overDataKey+" is not avalible please choose from the datasets:\n" + datasetstr)
                                if(overDataKey==""):
                                        overDataKey= "HaloID"


                datasets = extraDatasets + ["Mass","Radius","HaloID",",default Mass: "]
                datasetstr =  " ".join(datasets)

                orderDataKey = input("Please select which dataset you would like to set the order in which the dendograms are built:\n" + datasetstr)
                if (orderDataKey==""):
                        orderDataKey="Mass"
                while(orderDataKey not in datasets):
                        orderDataKey = input(orderDataKey+" is not avalible please choose from the datasets:\n" + datasetstr)
                        if (orderDataKey==""):
                                orderDataKey="Mass"

        else:

                #Otherwise lets get it from the configuration file
                sizeDataKey = plotOpt.markerSizeDataset
                colDataKey = plotOpt.markerColorDataset
                overplotDataset = plotOpt.overplotDataset
                orderDataKey = plotOpt.orderDataset
                binDataKey = plotOpt.binDataset

	# Lets load in the data
        for snap in range(opt.startSnap,opt.endSnap+1):

                snapKey = splitSnapKey %snap

                treedata[snapKey]["Redshift"] = np.float64(hdffile[snapKey].attrs["Redshift"])


                for key in requiredDatasets:

				#Make backwards compatible with the old ETF
                                if(key=="RootProgenitor"):
                                        treedata[snapKey]["StartProgenitor"] = np.array(hdffile[snapKey][key])

                                elif(key=="RootDescendant"):
                                        treedata[snapKey]["EndDescendant"] = np.array(hdffile[snapKey][key])

                                else:
                                        treedata[snapKey][key] = np.array(hdffile[snapKey][key])

                treedata[snapKey]["SizeData"] = np.array(hdffile[snapKey][sizeDataKey])
                treedata[snapKey]["ColData"] = np.array(hdffile[snapKey][colDataKey])
                if(plotOpt.overplotdata):
                        treedata[snapKey]["OverPlotData"] = np.array(hdffile[snapKey][overDataKey]) 
		

	#Find the indexes which the dendograms are to be plotted
        if(orderDataKey=="HaloID"):
                indexes=np.arange(plotOpt.nPlot)
        else:
                indexes=np.argsort(hdffile["Snap_%03d" %opt.endSnap][orderDataKey])[::-1][:plotOpt.nPlot]
                if(binDataKey=="Bin"):
                        # indexes in a bin of the property (ordered by the property itself)
                        tmp = hdffile["Snap_%03d" %opt.endSnap][orderDataKey]
                        indexes=np.where((hdffile["Snap_%03d" %opt.endSnap][orderDataKey][()]>plotOpt.lowBin)&(hdffile["Snap_%03d" %opt.endSnap][orderDataKey][()]<plotOpt.upBin))[0][:plotOpt.nPlot]

        hdffile.close()

        print("Done loading in data in",time.time()-start)

        return opt,treedata,indexes


