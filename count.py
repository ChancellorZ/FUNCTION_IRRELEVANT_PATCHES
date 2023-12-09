import json

import numpy as np,pickle
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
change_type=['FUNCTION_DECL', 'VAR_DECL', 'TYPEDEF_DECL', 'STRUCT_DECL', 'UNION_DECL', 'ENUM_DECL']
oss=['stable-linux','busybox','openssl']
noFunc=False
def query(arr,v):
	res=0
	for idx,num in enumerate(arr):
		if (idx&v)!=0:res+=num
	return res
def show1(mp):
	res=np.zeros([7,4*4])
	for idx,cnt in enumerate(mp):
		tool=0
		for x in range(6):
			for y in range(3):
				res[x][idx*4+y]+=cnt[1][1<<(x*3+y)]
				res[x][12+y]+=cnt[1][1<<(x*3+y)]
			k=query(cnt[0],7<<(x*3))
			res[x][idx*4+3]+=k
			res[x][15]+=k
			tool|=1<<(x*3)
		for y in range(3):
			k=query(cnt[0],tool<<y)
			res[6][idx*4+y]+=k
			res[6][12+y]+=k
		k=query(cnt[0],(1<<18)-1)
		res[6][idx*4+3]+=k
		res[6][15]+=k
	for y in range(16):
		for x in range(6):
			print(int(res[x][y]),end=' & ')
		print(int(res[6][y]),end='\\\\\n')
	print('------------------------------------------')
	return res
def step1(name):
	print("deal project: "+name)
	with open('commits_%s.pkl'%name,'rb')as f: data=pickle.load(f)
	print(name,len(data[0]),len(data[1]),end=' ')
	stable_commit , key_commit = data
	
	
	with open('res_%s.txt'%name,'r')as f: data=f.read()
	data=data.split('\n')
	idx=0
	cnt=[0]*(1<<(3*len(change_type)))
	cnt2=[0]*(1<<(3*len(change_type)))
	total=0
	success_commit_list = []
	success_nofunc_commit_list = []
	nofunc_file = 0
	while idx<len(data)-1:
		if not data[idx].startswith('{'):
			commit = data[idx].split('\t')[1]
			# print(data[idx].split('\t'))
			info = data[idx+1]
			info=json.loads(info)
			res=0
			if info['empty patch'] or len(info['success files'])==0:
				idx = idx + 2
				continue
			success_commit_list.append(commit)
			total+=1
			nofunc_file_temp = 0
			for sf in info['success files']:
				change=info['success files'][sf]['change kind']
				if "FUNCTION_DECL" not in change:
					if 'UNEXPOSED_DECL' in change:
						# print(change)
						if len(change)>1:
							nofunc_file = nofunc_file + 1
							nofunc_file_temp = nofunc_file_temp + 1
					else:
						nofunc_file_temp = nofunc_file_temp + 1
						nofunc_file = nofunc_file + 1
			
			success_nofunc_commit_list.append(commit+":"+str(nofunc_file_temp))
		idx = idx + 1
		# print(idx)
		
	print("all success commit:" + str(len(success_commit_list)))
	print("all success commit nofunc :" + str(len(success_nofunc_commit_list)))
	print("all success nofunc file: " + str(nofunc_file))
	stable_num = 0
	key_num = 0
	for commit in stable_commit:
		if commit in success_commit_list:
			stable_num = stable_num + 1
	for commit in key_commit:
		if commit in success_commit_list:
			key_num = key_num + 1
	print("stable commit: "+str(stable_num))
	print("key commit: "+str(key_num))
	
	
	while idx<len(data)-1:
		idx+=1
		info=data[idx]
		if info.startswith('{'):idx+=1
		else:continue
		info=json.loads(info)
		res=0
		if info['empty patch'] or len(info['success files'])==0:continue
		total+=1
		for sf in info['success files']:
			change=info['success files'][sf]['change kind']
		#if len(list(change.keys()))>0 and "FUNCTION_DECL" not in list(change.keys()):
			#	nofunc_num = nofunc_num + 1
			#print("####")
		#if "FUNCTION_DECL" not in change:nofunc_num=nofunc_num+1
			# items=change[tp].items()
			for tp in change:
				if tp=='UNEXPOSED_DECL':continue
				tp_id=change_type.index(tp)*3
				items=change[tp].items()
				#print(items)
				for ct,it in enumerate(items):
					if len(it[1])>0:
						res|=1<<(tp_id+ct)
		if noFunc==False or (res&7)==0:
			cnt[res]+=1
		# mask=0o222200
		# if res!=0 and (res|mask)==mask and (res&7)==0:
		# 	print(res,data[idx-2].split('\t')[-1])

	
	def solve(l,r):
		if l+1==r:
			cnt2[l]=cnt[l]
			return
		mid=(l+r)>>1
		solve(l,mid)
		solve(mid,r)
		for i in range(l,mid):cnt2[i]+=cnt2[i-l+mid]
	solve(0,len(cnt))
	print(total,)
	return(cnt,cnt2)
def most(res):
	x=[0]*(1<<18)
	y=[0]*18
	for cnt in res:
		for idx in range(1<<18):
			x[idx]+=cnt[1][idx]
		for idx in range(0,18):
			y[idx]+=cnt[0][1<<idx]
	x=list(enumerate(x+y))
	x.sort(key=lambda x:-x[1])
	i=j=0
	while(j<10):
		mask=x[i][0]
		num=x[i][1]
		i+=1
		if mask>=(1<<18):
			a,b=divmod(mask-(1<<18),3)
			print(['add','change','del'][b]+change_type[a],end='\t')
			print(num)
			j+=1
		elif (mask&-mask)!=mask:
			for a in range(0,6):
				for b in range(0,3):
					if ((1<<(a*3+b))&mask)!=0:
						print(['add','change','del'][b]+change_type[a],end='\t')
			print(num)
			j+=1
def calc(x):
	res=np.zeros([1<<18])
	for t in x:
		t=t[1]
		for idx in range(1<<18):
			res[idx]+=t[idx]
	cnt=0
	for i in range(1,1<<18):
		if res[i]!=0:cnt+=100
	print(cnt/((1<<18)-1),'%')
if __name__ == '__main__':
	# noFunc=True
	res1=[]
	for n in oss:res1.append(step1(n))
	calc(res1)
	mat1=show1(res1)
	# exit(0)
	noFunc=True
	res2=[]
	for n in oss: res2.append(step1(n))
	mat2=show1(res2)
	i2s=lambda x,y:"%d (%.2f\\%%)"%(x,100*x/y)
	for j in range(12,16):
		for i in range(1,7):
			print(i2s(mat2[i][j],mat1[i][j]),end=' & ')
		print(end='\\\\\n')
	print("----------------------------------")
	most(res1)
