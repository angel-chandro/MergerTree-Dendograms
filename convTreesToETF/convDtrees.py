import h5py
import numpy as np 
import time
import sys; #np.set_printoptions(threshold=sys.maxsize)
sys.path.append("..")
from cosFuncs import coshaloMvirToRvir  


def convDtreesToMTF(opt,snapKey,scalefactorKey,fieldsDict):

	halodata,redshiftData = loadDtreesData(opt.Dtreesfilename,opt.Nsnaps,opt.endSnap,snapKey,scalefactorKey,fieldsDict)

	treedata = convToMTF(opt.Nsnaps,halodata,fieldsDict,opt.h,opt.HALOIDVAL)

	return treedata, redshiftData


def setProgenRootHeads(mainProgenSnap,mainHaloID,mainProgenIndex,BranchRootDesc,treedata,HALOIDVAL):

	mainProgenSnapKey = "Snap_%03d" %mainProgenSnap

	#Find which halos point to this halo as a descendant
	progenIndexes = np.where(treedata[mainProgenSnapKey]["Descendant"]==mainHaloID)[0]

	#Get the main branches other progenitors
	progenIndexes = progenIndexes[progenIndexes!=mainProgenIndex]

	#Loop over the halos progenitors
	for progenIndex in progenIndexes:

		# Set the progen snapshot
		iprogenSnapKey = mainProgenSnapKey

		#Set its EndDescendant and this branches depth
		treedata[iprogenSnapKey]["EndDescendant"][progenIndex] = BranchRootDesc

		#Get the progenitor's haloID and its progenitor
		progenID = treedata[iprogenSnapKey]["Progenitor"][progenIndex]
		haloID = treedata[iprogenSnapKey]["HaloID"][progenIndex]	

		#Loop until the get to the last progenitor
		while(haloID!=progenID):

			#Get the progenitor's haloID and its progenitor
			progenID = treedata[iprogenSnapKey]["Progenitor"][progenIndex]
			haloID = treedata[iprogenSnapKey]["HaloID"][progenIndex]	

			#Find the progenitors snapshot
			iprogenSnap = treedata[iprogenSnapKey]["ProgenitorSnap"][progenIndex]

			#Find the index where this progenitor's haloID is
			progenIndex = treedata[iprogenSnapKey]["ProgenitorIndex"][progenIndex]

			iprogenSnapKey = "Snap_%03d" %iprogenSnap

			#Set its EndDescendant and its depth
			treedata[iprogenSnapKey]["EndDescendant"][progenIndex] = BranchRootDesc
			
			#Check if halo has any progeintors and walk down its tree
			if(np.sum(treedata[iprogenSnapKey]["Descendant"]==haloID)>1):
				treedata = setProgenRootHeads(iprogenSnap,haloID,progenIndex,BranchRootDesc,treedata,HALOIDVAL)

	return treedata


def convToMTF(numsnaps,halodata,fieldsDict,h,HALOIDVAL = 1000000000000):
        start = time.time()
        numhalos = np.zeros(numsnaps,dtype=np.int64)
        requiredFields = ["HaloID","StartProgenitor","Progenitor","Descendant","EndDescendant","Radius","Mass","Pos","HostHaloID","Redshift"]
        extraFields = [field for field in fieldsDict.keys() if field not in requiredFields]
        treedata = {"Snap_%03d" %snap:{} for snap in range(numsnaps)}
        doneflag = [[] for i in range(numsnaps)]
        haloiddict = {"Snap_%03d" %snap:{} for snap in range(numsnaps)}
        seachoffset = np.zeros(numsnaps,dtype=np.int64)
        for snap in range(numsnaps):
                snapKey = "Snap_%03d" %snap
                numhalos[snap] = len(halodata[snapKey]["HaloID"])
                doneflag[snap] = np.zeros(numhalos[snap],dtype=bool)
                treedata[snapKey]["EndDescendant"] = np.zeros(numhalos[snap],dtype=np.int64)
                treedata[snapKey]["Descendant"] = np.zeros(numhalos[snap],dtype=np.int64)
                treedata[snapKey]["HaloID"] = np.zeros(numhalos[snap],dtype=np.int64)
                treedata[snapKey]["Progenitor"] = np.zeros(numhalos[snap],dtype=np.int64)
                treedata[snapKey]["StartProgenitor"] = np.zeros(numhalos[snap],dtype=np.int64)
                treedata[snapKey]["DescendantIndex"]= np.zeros(numhalos[snap],dtype=np.int64)
                treedata[snapKey]["DescendantSnap"]= np.zeros(numhalos[snap],dtype=np.int32)
                treedata[snapKey]["ProgenitorIndex"]= np.zeros(numhalos[snap],dtype=np.int64)
                treedata[snapKey]["ProgenitorSnap"]= np.zeros(numhalos[snap],dtype=np.int32)
                treedata[snapKey]["HostHaloID"] = np.zeros(numhalos[snap],dtype=np.int64)
                halodata[snapKey]["Mass"] = halodata[snapKey]["Mass"]/h; halodata[snapKey]["Mass"] = halodata[snapKey]["Mass"]/1e10; treedata[snapKey]["Mass"] =halodata[snapKey]["Mass"].copy(); # Convert mass to 1e10*Msun/h units print('Mass:',treedata[snapKey]["Mass"])
                treedata[snapKey]["Radius"] = coshaloMvirToRvir(halodata[snapKey]["Mass"]*1e10)/1e3 #halodata[snapKey]["Radius"] = 2*halodata[snapKey]["Radius"]/h;  treedata[snapKey]["Radius"] = halodata[snapKey]["Radius"].copy() 

                halodata[snapKey]["Pos"] = halodata[snapKey]["Pos"]/h; treedata[snapKey]["Pos"] = halodata[snapKey]["Pos"].copy() 
                # halodata[snapKey]["Pos"] = None
                for extraField in extraFields:
                        treedata[snapKey][extraField]  = halodata[snapKey][extraField]
                        # halodata[snapKey][extraField] = None
		

                # Update the halo ID for the interpolated haloes
                sel = halodata[snapKey]["HaloID"]<1e16
                seachoffset[snap] = np.sum(sel)

                fileindex = ((halodata[snapKey]["HaloID"][sel]/1e8)%1e4).astype(np.int64); #print('fileindex:',fileindex)
                indexoffset = np.zeros(fileindex.size,dtype=np.int64)

                ifileindex = 0
                count =0 
                prevcount = 0
                for i in range(fileindex.size):
                        if(fileindex[i]!=ifileindex):
                                prevcount=count
                                ifileindex+=1
                        indexoffset[i]+=prevcount
                        count+=1

                print('indexoffset:',indexoffset)
                print(halodata[snapKey]["HaloID"])
                print('THEREARE',halodata[snapKey]["HaloID"].size)
                s = np.shape(np.where(sel==True))[1]; print(s)
                treedata[snapKey]["HaloID"][sel] = snap* HALOIDVAL + np.arange(0,s) +1#halodata[snapKey]["HaloID"][sel] - (fileindex*1e8).astype(np.int64) + indexoffset;
                #treedata[snapKey]["HaloID"][sel] = halodata[snapKey]["HaloID"][sel] - (fileindex*1e8).astype(np.int64) + indexoffset; #print('NoI:',treedata[snapKey]["HaloID"][sel]) # there is an overlap between non-interpolated and interpolated ones: remove the +1 in non-interpolated IDs

                treedata[snapKey]["HaloID"][~sel] = snap * HALOIDVAL + np.arange(s,halodata[snapKey]["HaloID"].size) +1#np.arange(seachoffset[snap],halodata[snapKey]["HaloID"].size) +1; #print('I:',treedata[snapKey]["HaloID"][~sel])

		#Change the host halo ID for interpolated hosts
		# haloiddict[snapKey] = dict(zip(halodata[snapKey]["HaloID"][~sel],treedata[snapKey]["HaloID"][~sel]))
		# interphostsel = halodata[snapKey]["HostHaloID"]>1e16
		# interphostindices = np.where(interphostsel)[0]
		# for indx in interphostindices:
		# 	treedata[snapKey]["HostHaloID"][indx] = haloiddict[snapKey][halodata[snapKey]["HostHaloID"][indx]]
		# treedata[snapKey]["HostHaloID"][~interphostsel] = halodata[snapKey]["HostHaloID"][~interphostsel]

		# #If the are pointing to themselves then set the host halo ID to -1
		# fieldhaloindex = np.where(treedata[snapKey]["HostHaloID"]==treedata[snapKey]["HaloID"])[0]
		# treedata[snapKey]["HostHaloID"][fieldhaloindex] = -1


        print("Setting Descendants")

        for snap in range(numsnaps-1,-1,-1):

                start2=time.time()

                snapKey = "Snap_%03d" %snap

                haloDict = dict(zip(halodata[snapKey]["HaloID"],treedata[snapKey]["HaloID"]))#; print('Dict:',haloDict)

                if(snap>0):
                        nextSnapKey = "Snap_%03d" %(snap-1)

                        treedata[nextSnapKey]["Descendant"] = halodata[nextSnapKey]["Descendant"].copy()

                        if(any(halodata[nextSnapKey]["Descendant"]>-1)):
                                indexes = np.where(halodata[nextSnapKey]["Descendant"]>-1)[0]

                                for idx,ihalo in zip(indexes,halodata[nextSnapKey]["Descendant"][indexes]):
					#print(idx,ihalo,haloDict[ihalo])
                                        print('idx:',idx); print('ihalo:',ihalo); print('haloDict[ihalo]:',haloDict[ihalo])
                                        treedata[nextSnapKey]["Descendant"][idx] = haloDict[ihalo]; #print('idx:',idx); print('ihalo:',ihalo); print('haloDict[ihalo]:',haloDict[ihalo])
                                        # look for the descendant index in the reduced catalogue
                                        print(treedata[snapKey]["HaloID"])
                                        print(treedata[nextSnapKey]["Descendant"][idx])
                                        print('Hereare:',np.where(treedata[snapKey]["HaloID"]==treedata[nextSnapKey]["Descendant"][idx])[0])
                                        treedata[nextSnapKey]["DescendantIndex"][idx] = np.where(treedata[snapKey]["HaloID"]==treedata[nextSnapKey]["Descendant"][idx])[0]
                                        #treedata[nextSnapKey]["DescendantIndex"][idx] = int(haloDict[ihalo]%HALOIDVAL-1); #print('Check:',treedata[nextSnapKey]["DescendantIndex"][idx])

                        treedata[nextSnapKey]["DescendantSnap"] = halodata[nextSnapKey]["DescendantSnap"]

		#If the are pointing to themselves then set the host halo ID to -1
                fieldhaloindex = halodata[snapKey]["HostHaloID"]==halodata[snapKey]["HaloID"]
                treedata[snapKey]["HostHaloID"][fieldhaloindex] = -1

                haveHost = np.where(~fieldhaloindex)[0]
                for ihaveHost in haveHost:
                        treedata[snapKey]["HostHaloID"][ihaveHost] = haloDict[halodata[snapKey]["HostHaloID"][ihaveHost]]

                print("Done snap",snap,"in",time.time()-start2)


        treedata["Snap_%03d" %(numsnaps-1)]["Descendant"][:] = -1
        treedata["Snap_%03d" %(numsnaps-1)]["DescendantSnap"][:] = numsnaps-1

        print("Done setting Descendants in",time.time()-start)
        start=time.time()

        print("Setting Halos Progenitors and StartProgenitors")
	# for snap in range(numsnaps):

	# 	snapKey = "Snap_%03d" %snap
	# 	print("Doing snap",snap)



	# 	for ihalo in range(numhalos[snap]):

	# 		if(treedata[snapKey]["Progenitor"][ihalo]==0):

	# 			#Set the new haloID
	# 			# if(halodata[snapKey]["HaloID"][ihalo]>1e16):
	# 			# 	treedata[snapKey]["HaloID"][ihalo] = snap*HALOIDVAL + ihalo + 1

	# 			#Set the data for the current halo 
	# 			currIndex = ihalo
	# 			currSnap = snap
	# 			currSnapKey = "Snap_%03d" %currSnap


	# 			#Set the Branches StartProgenitor
	# 			BranchStartProgenitor = treedata[currSnapKey]["HaloID"][currIndex]
	# 			treedata[currSnapKey]["StartProgenitor"][currIndex] = BranchStartProgenitor
	# 			treedata[currSnapKey]["Progenitor"][currIndex] = BranchStartProgenitor
	# 			treedata[currSnapKey]["ProgenitorSnap"][currIndex] = currSnap
	# 			treedata[currSnapKey]["ProgenitorIndex"][currIndex] =currIndex

	# 			#Loop over this branch setting the Descendant, Progenitor and StartProgenitor
	# 			while(True):

	# 				#Extract the descendant
	# 				DescID = halodata[currSnapKey]["Descendant"][currIndex]

	# 				#Check to see if we have reached the EndDescendant of this branch
	# 				if(DescID==-1):
	# 					treedata[currSnapKey]["Descendant"][currIndex] = treedata[currSnapKey]["HaloID"][currIndex]
	# 					treedata[currSnapKey]["DescendantSnap"][currIndex] = currSnap
	# 					treedata[currSnapKey]["DescendantIndex"][currIndex] = currIndex
	# 					treedata[currSnapKey]["EndDescendant"][currIndex] = treedata[currSnapKey]["HaloID"][currIndex]
	# 					break

						
	# 				#Get the descendants snapshot
	# 				if((DescID/1e16)>1):
	# 					descSnap = treedata[currSnapKey]["DescendantSnap"][currIndex]
	# 					descSnapKey = "Snap_%03d" %descSnap
	# 					descIndex = int(np.where(halodata[descSnapKey]["HaloID"][seachoffset[int(descSnap)]:]==DescID)[0] + seachoffset[int(descSnap)])

	# 					#Convert the descendant ID to updated ID
	# 					treedata[currSnapKey]["Descendant"][currIndex] = descSnap*HALOIDVAL + descIndex + 1
	# 				else: 
	# 					descSnap = treedata[currSnapKey]["DescendantSnap"][currIndex]
	# 					descSnapKey = "Snap_%03d" %descSnap
	# 					descIndex = treedata[currSnapKey]["DescendantIndex"][currIndex]

	# 					#Convert the descendant ID to updated ID
	# 					treedata[currSnapKey]["Descendant"][currIndex] = DescID


	# 				#Check to see if this Progenitor ID has already be done
	# 				if(treedata[descSnapKey]["Progenitor"][descIndex]>0):
	# 					break

	# 				# print(treedata[descSnapKey]["Progenitor"][descIndex],treedata[currSnapKey]["HaloID"][currIndex],halodata[descSnapKey]["isMainProgenitor"][descIndex])
	# 				#Set the Progenitor and StartProgenitor only if main progenitor or it involves a is a filler halo (has ID > 1e16)
	# 				if(halodata[descSnapKey]["isMainProgenitor"][descIndex] | (descSnap==numsnaps-1)):
	# 					treedata[descSnapKey]["StartProgenitor"][descIndex] = BranchStartProgenitor
	# 					treedata[descSnapKey]["Progenitor"][descIndex] = treedata[currSnapKey]["HaloID"][currIndex]
	# 					treedata[descSnapKey]["ProgenitorIndex"][descIndex] = currIndex 
	# 					treedata[descSnapKey]["ProgenitorSnap"][descIndex] = currSnap

	# 				#Move up so the current halo is the descendant
	# 				currIndex = descIndex
	# 				currSnap = descSnap
	# 				currSnapKey = "Snap_%03d" %currSnap



        for isnap in range(numsnaps):

                currSnapKey = "Snap_%03d" %isnap

                start2=time.time()
                if (numhalos[isnap] == 0): continue
                #set Progenitors and root Progenitors if necessary
                indices = np.where(treedata[currSnapKey]['Progenitor'] == 0)[0]
                numareStartProgenitors = indices.size

                if (numareStartProgenitors > 0):
                        treedata[currSnapKey]['Progenitor'][indices] = np.array(treedata[currSnapKey]['HaloID'][indices],copy=True)
                        treedata[currSnapKey]['StartProgenitor'][indices] = np.array(treedata[currSnapKey]['HaloID'][indices],copy=True)
                        treedata[currSnapKey]['ProgenitorSnap'][indices] = isnap*np.ones(indices.size, dtype=np.int32)
                        treedata[currSnapKey]['ProgenitorIndex'][indices] = np.array(indices,dtype=np.int64,copy=True)

                descencheck = treedata[currSnapKey]["Descendant"]!=-1; print(descencheck)
                indices = np.where(~descencheck)[0]

		#find all halos that have descendants and set there heads
                if (indices.size):
                        treedata[currSnapKey]["Descendant"][indices] = np.array(treedata[currSnapKey]["HaloID"][indices],copy=True)
                        treedata[currSnapKey]["DescendantSnap"][indices] = isnap
                        treedata[currSnapKey]["DescendantIndex"][indices] = indices
                        treedata[currSnapKey]["EndDescendant"][indices] = np.array(treedata[currSnapKey]["HaloID"][indices],copy=True)


                indices=np.where(descencheck)[0]; print(indices)
                numwithdescen = indices.size

                if (numwithdescen>0):

                        interpdescen = np.where(treedata[currSnapKey]["Descendant"]>1e16)[0]; #print('Int:',interpdescen)
                        descSnap = isnap + 1
                        descSnapKey = "Snap_%03d" %descSnap

			# interpdescenindices = (np.where(np.in1d(halodata[descSnapKey]["HaloID"][seachoffset[int(descSnap)]:],treedata[currSnapKey]["Descendant"][interpdescen]))[0] + seachoffset[int(descSnap)]).astype(np.int64)

                        for indx in interpdescen:
                                treedata[currSnapKey]["Descendant"][indx] = haloiddict[descSnapKey][halodata[currSnapKey]["Descendant"][indx]]

                        treedata[currSnapKey]["DescendantIndex"][interpdescen] = (treedata[currSnapKey]["Descendant"][interpdescen]%(HALOIDVAL/1e4)).astype(np.int64); #print((treedata[currSnapKey]["Descendant"][interpdescen]%(HALOIDVAL/1e4)).astype(np.int64))

			# set the Progenitors of all these objects and their root Progenitors as well
                        indices2 = np.where(halodata[currSnapKey]["isMainProgenitor"][indices]==1)[0]
                        numactive = indices2.size
                        if (numactive>0):
                                activeProgenitors = indices[indices2]#; print('1:',indices[indices2]); print('2:',treedata[currSnapKey]["DescendantIndex"][indices]); print('3:',indices2); print('4:',indices)
                                descenindex = treedata[currSnapKey]["DescendantIndex"][indices[indices2]]#; print('descSnapKey:',descSnapKey); print('descenindex:',descenindex); print(treedata[descSnapKey]['Progenitor']); print(np.shape(treedata[descSnapKey]['Progenitor'])); #print(np.shape(treedata[currSnapKey]['HaloID']))
                                
                                treedata[descSnapKey]['Progenitor'][descenindex] = treedata[currSnapKey]['HaloID'][activeProgenitors]
                                treedata[descSnapKey]['StartProgenitor'][descenindex] = treedata[currSnapKey]['StartProgenitor'][activeProgenitors]
                                treedata[descSnapKey]['ProgenitorSnap'][descenindex] = isnap
                                treedata[descSnapKey]['ProgenitorIndex'][descenindex] = activeProgenitors

                print("Done snap",isnap,"in",time.time()-start2)

        print("Done seeting the Progenitors,Descendants and StartProgenitors in",time.time()-start)

	#raise SystemExit()
        print("Setting all the RootHead ID's")

	# #Now we have built the Progenitors, Descendants and StartProgenitors, we need to now go back down the branches setting the RootDescedant for the halos
	# for snap in range(numsnaps-1,-1,-1):

	# 	print("Doing snap",snap)

	# 	snapKey = "Snap_%03d" %snap

	# 	for ihalo in range(numhalos[snap]):

	# 		if(treedata[snapKey]["EndDescendant"][ihalo]):

	# 			BranchRootDesc = treedata[snapKey]["EndDescendant"][ihalo] 

	# 			mainProgenSnap = snap
	# 			mainProgenSnapKey = "Snap_%03d" %mainProgenSnap
	# 			mainProgenIndex = ihalo

	# 			mainHaloID = treedata[mainProgenSnapKey]["HaloID"][mainProgenIndex]
	# 			mainProgenID = treedata[mainProgenSnapKey]["Progenitor"][mainProgenIndex]

	# 			while(mainHaloID!=mainProgenID):

	# 				mainHaloID = treedata[mainProgenSnapKey]["HaloID"][mainProgenIndex]
	# 				mainProgenID = treedata[mainProgenSnapKey]["Progenitor"][mainProgenIndex]
	# 				mainProgenSnap = treedata[mainProgenSnapKey]["ProgenitorSnap"][mainProgenIndex]

	# 				mainProgenIndex = treedata[mainProgenSnapKey]["ProgenitorIndex"][mainProgenIndex] #np.where(treedata[mainProgenSnapKey]["HaloID"]==mainProgenID)[0]

	# 				treedata = setProgenRootHeads(mainProgenSnap,mainHaloID,mainProgenIndex,BranchRootDesc,treedata,HALOIDVAL)

	# 				mainProgenSnapKey = "Snap_%03d" % mainProgenSnap
	# 				treedata[mainProgenSnapKey]["EndDescendant"][mainProgenIndex] = BranchRootDesc

        start = time.time()

	# first set root heads of main branches
        for isnap in range(numsnaps-1,0,-1):
                if (numhalos[isnap] == 0):
                        continue
                snapKey = "Snap_%03d" %isnap
                indices = np.where((treedata[snapKey]['EndDescendant'] != 0) & (treedata[snapKey]["Progenitor"]!=treedata[snapKey]["HaloID"]))[0]
                numactive=indices.size

                if (numactive == 0):
                        continue

                progenindexarray = treedata[snapKey]['ProgenitorIndex'][indices]


                progensnap = isnap -1
                progenSnapKey = "Snap_%03d" %progensnap
                # go to root Progenitors and walk the main branch
                treedata[progenSnapKey]['EndDescendant'][progenindexarray]=treedata[snapKey]['EndDescendant'][indices]
	# print("Done 1 in", time.time()-start)
	# start = time.time()

	# for isnap in range(numsnaps-1,-1,-1):
	# 	if (numhalos[isnap] == 0):
	# 		continue
	# 	# identify all haloes which are not primary progenitors of their descendants, having a descendant rank >0
	# 	snapKey = "Snap_%03d" %isnap
	# 	indices = np.where(treedata[snapKey]['isMainProgenitor'] == 0)[0]
	# 	numactive = indices.size
	# 	if (numactive == 0):
	# 		continue

	# 	allhaloid = treedata[snapKey]["HaloID"][indices]
	# 	maindescen = treedata[snapKey]["Descendant"][indices]
	# 	maindescenindex = treedata[snapKey]["DescendantIndex"][indices]
	# 	maindescensnap = treedata[snapKey]["DescendantSnap"][indices]

	# 	# for each of these haloes, set the head and use the root head information and root snap and set all the information
	# 	# long its branch
	# 	for i in range(numactive):
	# 		# store the root head
	# 		# now set the head of these objects
	# 		halosnap = isnap
	# 		haloID = allhaloid[i]
	# 		iSnapKey = "Snap_%03d" %halosnap
	# 		haloindex = indices[i]
	# 		# increase the number of progenitors of this descendant
	# 		maindescensnapkey = "Snap_%03d" %maindescensnap[i]
	# 		roothead = treedata[maindescensnapkey]['EndDescendant'][maindescenindex[i]]
	# 		# now set the root head for all the progenitors of this object
	# 		while (True):
	# 			iSnapKey = "Snap_%03d" %halosnap
	# 			treedata[iSnapKey]['EndDescendant'][haloindex] = roothead
	# 			if (haloID == treedata[iSnapKey]['Progenitor'][haloindex]):
	# 				break
	# 			haloid = treedata[iSnapKey]['Progenitor'][haloindex]
	# 			tmphaloindex = treedata[iSnapKey]['ProgenitorIndex'][haloindex]
	# 			halosnap = treedata[iSnapKey]['ProgenitorSnap'][haloindex]
	# 			haloindex = tmphaloindex

	# print("Done 2 in", time.time()-start)
        start = time.time()
        for isnap in range(numsnaps-2,-1,-1):
                if (numhalos[isnap] == 0):
                        continue
                # identify all haloes which are not primary progenitors of their descendants, having a descendant rank >0
                snapKey = "Snap_%03d" %isnap
                indices = np.where(treedata[snapKey]['EndDescendant'] == 0)[0]
                numactive = indices.size
                if (numactive == 0):
                        continue

                allhaloid = treedata[snapKey]["HaloID"][indices]
                maindescen = treedata[snapKey]["Descendant"][indices]
                maindescenindex = treedata[snapKey]["DescendantIndex"][indices]

                maindescensnap = isnap+1
                descSnapKey = "Snap_%03d" %maindescensnap; #print('1:',maindescenindex); print('2:',indices); print(treedata[snapKey]["EndDescendant"]); print(treedata[descSnapKey]['EndDescendant'])


                treedata[snapKey]["EndDescendant"][indices] = treedata[descSnapKey]['EndDescendant'][maindescenindex]


        print("Done setting the EndDescendants in",time.time()-start)

        return treedata

def loadDtreesData(basefilename,numsnaps,endsnap,snapKey,scalefactorKey,dataKeys):

        #Lets find out how many subvolumes there are and the datatype of each field
        filename = basefilename + ".0.hdf5"
        hdffile = h5py.File(filename,"r")
        nfiles = 1 #hdffile["fileInfo"].attrs["numberOfFiles"][...]
        fielddatatypes = {datakey:hdffile[dataKeys[datakey]].dtype for datakey in dataKeys.keys()}
        hdffile.close()
        
	#Find the number of haloes per subvolume, field datatypes and the scalefactor
        numhalospersubvol = np.zeros(nfiles,dtype = np.int64)
        for ivol in range(nfiles):
                filename = basefilename + "." + str(ivol) + ".hdf5"
                hdffile = h5py.File(filename,"r")

                #Load the redshift data
                redshiftData = hdffile[scalefactorKey][:]
                pad = np.zeros(numsnaps - len(redshiftData))
                redshiftData = np.concatenate([pad,redshiftData])

		#Extract the number of haloes  
                numhalospersubvol[ivol] = hdffile["haloTrees/nodeIndex"].size; #descID = np.array(hdffile["haloTrees/descendantIndex"][()],dtype='int64'); haloID = np.array(hdffile["haloTrees/nodeIndex"][()],dtype='int64'); print('1:',np.where(haloID==10197000000043139)); print('2:',np.where(descID==10197000000043139)); print('Total halos:',haloID.size); ind1 = np.where(descID==-1); print("Descendants=-1:",ind1[0]); ind2 = np.isin(descID,haloID); print(ind2); h2 = np.where(ind2==True); print('HERE',h2[0]); indT = np.sort(np.concatenate((ind1[0],h2[0]))); print(indT); print(indT.size); print('3:',np.where(indT==73349)); print('4:',haloID[73349]); numhalospersubvol[ivol] = indT.size
                hdffile.close()

        totnhalos = np.sum(numhalospersubvol,dtype=np.uint64) 

	#Now load in the snapshot to find how many objects per snapshot
        snapshots = np.zeros(totnhalos,dtype=np.int64)
        offset = 0
        for ivol in range(nfiles):

                filename = basefilename + "." + str(ivol) + ".hdf5"
                hdffile = h5py.File(filename,"r")

		#Insert the snapshot dataset
                snapshots[offset:offset+numhalospersubvol[ivol]] = hdffile["haloTrees/snapshotNumber"]

                hdffile.close()
                offset+=numhalospersubvol[ivol]



	#Find out the number of objects per snapshot
        uniquesnaps,counts = np.unique(snapshots,return_counts=True)
        minsnap = np.min(uniquesnaps)
        snapcounts = np.zeros(numsnaps,dtype=np.int64)
        for snap in range(minsnap,numsnaps):
                sel = np.where(uniquesnaps==snap)[0]
                if(sel.size>0):
                        snapcounts[snap] = counts[sel]


	#Setup the arrays to store the data
        halodata = {"Snap_%03d" %snap:{dataKey:(np.zeros([snapcounts[snap],3],dtype=fielddatatypes[dataKey]) if((dataKey=="Pos") | (dataKey=="Vel") | (dataKey=="AngMom")) else np.zeros(snapcounts[snap],dtype=fielddatatypes[dataKey])) for dataKey in dataKeys.keys()} for snap in range(numsnaps)}
        offset = 0
        snapoffsets = np.zeros(numsnaps,dtype=np.int64)

	#Extract its redshift
        for snap in range(numsnaps):
                snapKey = "Snap_%03d" %snap
                halodata[snapKey]["Redshift"] = redshiftData[snap]

	#Loop over all the volume files and load in the data
        for ivol in range(nfiles):

                print("Loading data from file",ivol)

                filename = basefilename + "." + str(ivol) + ".hdf5"
                hdffile = h5py.File(filename,"r")

		#Open up the arrays for quick access
                tmpData = {key:hdffile[key][:]   for key in dataKeys.values()}

		# Now we can load in the data, splitting it across snapshots for quicker searching
                for snap in range(minsnap,numsnaps):

                        snapKey = "Snap_%03d" %snap

			#Find the data which fall into this snapshot
                        snapSel = np.where(snapshots[offset:offset+numhalospersubvol[ivol]]==snap)[0].tolist()

			#Find the number of haloes in this snapshot in this file
                        isnapnumhaloes = len(snapSel)

			#Extract the data
                        for dataKey in dataKeys.keys():
                                halodata[snapKey][dataKey][snapoffsets[snap]:snapoffsets[snap]+isnapnumhaloes] = tmpData[dataKeys[dataKey]][snapSel]

                        snapoffsets[snap]+=isnapnumhaloes

                offset+=numhalospersubvol[ivol]
                hdffile.close()

	#Sort all the datasets so they are in HaloID order
        for snap in range(minsnap,numsnaps):

                snapKey = "Snap_%03d" %snap; print(snapKey)


                sortIndx = np.argsort(halodata[snapKey]["HaloID"]); print(sortIndx.size)
                
                for dataKey in dataKeys.keys():
                        halodata[snapKey][dataKey] = halodata[snapKey][dataKey][sortIndx]

                # not all the files: set descID==-1 when the descendant is in anther file
                if snap<endsnap:

                        descsnapKey = "Snap_%03d" %(snap+1); print('desc:',descsnapKey)

                        haloID = halodata[descsnapKey]["HaloID"]
                        descID = halodata[snapKey]["Descendant"]
                        indT = np.isin(descID,haloID)
                        print('indT:',indT)
                        ind = np.where(indT==False)
                        halodata[snapKey]["Descendant"][ind] = -1
                
        return halodata,redshiftData


