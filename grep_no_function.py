import json

import clang.cindex,pickle

import conf
import utils,pygit2,os,threading,shutil
clang.cindex.Config.set_library_file(conf.libclangPath)
# processed_commits
processed_commits=[]
if os.path.exists('processed.txt'):
	with open('processed.txt','r') as f:
		for x in f.read().split('\n'):
			x=x.strip('\n')
			if len(x)==0: continue
			processed_commits.append(x)
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
			res.setdefault('parse except files',[])
			res['parse except files'].append(x)
	return res
def get_bug_patch(repo):
	if os.path.exists('commits.pkl'):
		with open('commits.pkl','rb')as f: commit_set=pickle.load(f)
		return commit_set
	commit_setA=set()
	good_pattern=['bugzilla','coverity']
	for branch in repo.branches:
		if not branch.endswith('y'): continue
		branch=repo.branches[branch]
		for commit in repo.walk(branch.target):
			commit_setA.add(commit.hex)
	print('case 1:',len(commit_setA))
	commit_setB=set()
	for commit in repo.walk(repo.head.target):
		for pattern in good_pattern:
			if pattern in commit.message.lower():
				commit_setB.add(commit.hex)
				commit_setA.add(commit.hex)
	print('case 2:',len(commit_setB))
	with open('commits.pkl','wb')as f: pickle.dump(commit_setA,f)
	return commit_setA
def solve_bundle(id,repo):
	global need_feed_id,total_thread,processed_commits
	this_dir='files/%d/'%id
	while True:
		has_data[id].acquire()
		if go_die[id]:
			die_rw.acquire()
			total_thread-=1
			die_rw.release()
			return
		total_res=""
		if not os.path.exists(this_dir):os.mkdir(this_dir)
		for commit in feed_data[id]:
			try:
				print("thread %d is processing %s"%(id,commit))
				scan_res=scan_commit(commit,this_dir,repo)
				total_res+="%s\t%s\n%s\n"%(repo.workdir,commit,json.dumps(scan_res))
			except Exception as e:print(e)
		processed_rw.acquire()
		processed_commits+=feed_data[id]
		with open('processed.txt','a') as f:
			for commit in feed_data[id]:
				f.write(commit+'\n')
		processed_rw.release()
		res_rw.acquire()
		with open('ress.txt','a') as f:
			f.write(total_res)
		res_rw.release()
		try: shutil.rmtree(this_dir)
		except: pass
		need_feed.acquire()
		need_feed_id=id
		should_feed.release()
def one_oss(repo_path):
	repo=pygit2.Repository(repo_path+'/.git')
	bug_patch=list(get_bug_patch(repo))
	index=0
	def get_nxt():
		nonlocal index
		left=index
		index=min(index+conf.step,len(bug_patch))
		res=[]
		processed_rw.acquire()
		for x in range(left,index):
			commit=bug_patch[x]
			if not commit in processed_commits:res.append(commit)
		processed_rw.release()
		return res,index-left
	for id in range(conf.pool_size):
		feed_data[id],sz=get_nxt()
		t1=threading.Thread(target=solve_bundle,args=(id,repo))
		t1.start()

	while total_thread>0:
		should_feed.acquire()
		feed_data[need_feed_id],sz=get_nxt()
		if sz==0:go_die[need_feed_id]=True
		has_data[need_feed_id].release()
		need_feed.release()
if __name__ == '__main__':
	one_oss(conf.project_root+'oss/stable-linux')
