import json

import clang.cindex,pickle

import conf
import utils,pygit2,os,threading,shutil
clang.cindex.Config.set_library_file(conf.libclangPath)
# processed_commits
processed_commits=set()
if os.path.exists('processed.txt'):
	with open('processed.txt','r') as f:
		for x in f.read().split('\n'):
			x=x.strip('\n')
			if len(x)==0: continue
			processed_commits.add(x)
processed_rw=threading.Semaphore(1)

# sub_thread_pool
total_thread=conf.pool_size
die_rw=threading.Semaphore(1)
sub_thread_pool_s=threading.Semaphore(conf.pool_size)
sub_thread_pool=list(range(conf.pool_size))
pool_rw=threading.Semaphore(1)

feed_data=[[]for x in range(conf.pool_size)]
go_die=[False]*conf.pool_size
has_data=[threading.Semaphore(1)for x in range(conf.pool_size)]
need_feed=threading.Semaphore(1)
should_feed=threading.Semaphore(0)
need_feed_id=0
# res
res_rw=threading.Semaphore(1)

def scan_commit(commit_id,path,repo):
	if not os.path.exists(path):
		os.makedirs(path)
	after=repo.revparse_single(commit_id)
	before=repo.revparse_single(commit_id+"^")
	patches=repo.diff(before,after)
	files=[]
	patches=patches.patch
	res={'strange file':[],'except file':[],'empty patch':False}
	if patches==None:
		res['empty patch']=True
		return res
	patches=patches.split('\n')
	idx=0
	while idx<len(patches):
		p=idx+1
		while p<len(patches) and not patches[p].startswith('diff'): p=p+1
		data=patches[idx:p]
		idx=p
		if data[0].startswith('diff'):
			l=data[0].split(' ')
			fa=l[2]
			fb=l[3]
			d=''
			for t in data: d=d+t+'\n'
			if fa.startswith('a/') \
					and fb.startswith('b/') \
					and fa[2:]==fb[2:] \
					and (fa.endswith('.c') or fa.endswith('.h'))\
					and before.tree.__contains__(fa[2:])\
					and after.tree.__contains__(fb[2:]):
				files.append(fa[2:])
			else:
				res.setdefault('strange files',[])
				res['strange files'].append([fa,fb])
	res['success files']={}
	for x in files:
		xx=x[x.rfind('/')+1:-2]
		ad=before.tree[x].data
		bd=after.tree[x].data
		af=path+('%s_a.c'%xx)
		bf=path+('%s_b.c'%xx)
		with open(af,'wb')as f: f.write(ad)
		with open(bf,'wb')as f: f.write(bd)
		try:
			ci=utils.change_info(af,bf)
			ret=ci.solve()
			res['success files'][x]=ret
		except Exception as e:
			print(e)
			res.setdefault('parse except files',[])
			res['parse except files'].append(x)
	return res
def get_bug_patch(repo,name,goodb,pattern):
	if os.path.exists('commits_%s.pkl'%name):
		with open('commits_%s.pkl'%name,'rb')as f: commit_setA,commit_setB=pickle.load(f)
		return commit_setA|commit_setB
	tag_set=set()
	for ref in repo.references:
		if not 'tag' in ref.lower():continue
		ref=repo.references[ref]
		cid=repo[ref.target.hex]
		if type(cid)==pygit2.Tag:
			cid=cid.target.hex
		else:
			cid=cid.hex
		tag_set.add(cid)
	commit_setA=set()
	good_pattern=['bugzilla','coverity']
	for branch in repo.branches:
		if not branch.endswith(goodb): continue
		branch=repo.branches[branch]
		for commit in repo.walk(branch.target):
			if not commit in tag_set and pattern(commit.message):
				commit_setA.add(commit.hex)
	print('case 1:',len(commit_setA))
	commit_setB=set()
	for commit in repo.walk(repo.head.target):
		for pattern in good_pattern:
			if pattern in commit.message.lower():
				commit_setB.add(commit.hex)
	print('case 2:',len(commit_setB))
	with open('commits_%s.pkl'%name,'wb')as f: pickle.dump((commit_setA,commit_setB),f)
	return commit_setA|commit_setB

def one_oss(repo_name,goodb,pattern):
	repo_path=conf.project_root+'oss/'+repo_name
	repo=pygit2.Repository(repo_path+'/.git')
	feed_data=get_bug_patch(repo,repo_name,goodb,pattern)
	# feed_data=['74ede0ff59fb18787213ed979641624a2f234821']
	this_dir='files/%s/'%repo_name
	if not os.path.exists(this_dir):os.mkdir(this_dir)
	for commit in feed_data:
		if commit in processed_commits:continue
		total_res=""
		try:
			print("processing %s"%commit)
			scan_res=scan_commit(commit,this_dir,repo)
			total_res+="%s\t%s\n%s\n"%(repo.workdir,commit,json.dumps(scan_res))
		except Exception as e:print(e)
		processed_commits.add(commit)
		with open('processed_%s.txt'%repo_name,'a') as f:
				f.write(commit+'\n')
		with open('res_%s.txt'%repo_name,'a') as f:
			f.write(total_res)
if __name__ == '__main__':
	one_oss('busybox','stable',lambda x:True)
	one_oss('openssl','stable',lambda x:True)
	one_oss('stable-linux','.y',lambda x:('[patch]'in x.lower()))