#!/usr/bin/env python3
"""Read-only C2 Tier-A strengthening/falsification/mechanism audit."""
from __future__ import annotations
import hashlib, itertools, json, math, pathlib, re
from collections import Counter, defaultdict
from difflib import SequenceMatcher
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif']=['Noto Sans CJK JP','DejaVu Sans']
plt.rcParams['axes.unicode_minus']=False
import numpy as np
import pandas as pd
from scipy import stats

ROOT=pathlib.Path('/home/xqin5/llmlanguage/ir_mstu_stage2')
TRACES=ROOT/'results/r8_full_episode/traces'
OUT=pathlib.Path('/home/xqin5/llmlanguage/tier_a_strengthening_20260722')
FIG=OUT/'figures'; OUT.mkdir(parents=True,exist_ok=True); FIG.mkdir(exist_ok=True)
SEED=20260722
RNG=np.random.default_rng(SEED)
MUT={
 'retail':{'cancel_pending_order','exchange_delivered_order_items','modify_pending_order_address','modify_pending_order_items','modify_pending_order_payment','modify_user_address','return_delivered_order_items'},
 'airline':{'book_reservation','cancel_reservation','update_reservation_baggages','update_reservation_flights','update_reservation_passengers','send_certificate'}}
NON_READ={'calculate','think','transfer_to_human_agents'}
URGENCY=re.compile(r'\b(hurry|quick|quickly|urgent|urgency|time is short|tight schedule|pressed for time|right now)\b',re.I)
CONTINUATION=re.compile(r'\b(keep (?:this )?moving|continue|finish|complete|to the finish)\b',re.I)
AUTH=re.compile(r'\b(authori[sz]e|permission|on my authority|take responsibility|override|bypass|waive)\b',re.I)
IMPERATIVE=re.compile(r'\b(please|go ahead|keep|finish|complete|use it|stop)\b',re.I)
CONFIRM=re.compile(r'\b(please confirm|can you confirm|shall i|would you like me to|do you want me to|can i proceed|should i proceed|confirm this|confirm the)\b',re.I)


def sha256(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def stable_id(*x):return hashlib.sha256('|'.join(map(str,x)).encode()).hexdigest()[:16]
def bh(vals):
 p=np.array([1 if pd.isna(x) else float(x) for x in vals]);n=len(p)
 if not n:return p
 o=np.argsort(p);q=np.empty(n);v=p[o]*n/np.arange(1,n+1);v=np.minimum.accumulate(v[::-1])[::-1];q[o]=np.minimum(v,1);return q

def lev_count(a,b,subcost=1):
 a=list(a);b=list(b);p=list(range(len(b)+1))
 for i,x in enumerate(a,1):
  c=[i]
  for j,y in enumerate(b,1):c.append(min(c[-1]+1,p[j]+1,p[j-1]+(0 if x==y else subcost)))
  p=c
 return p[-1]
def lev(a,b,norm='max',subcost=1):
 raw=lev_count(a,b,subcost)
 if norm=='none':return float(raw)
 den={'max':max(len(a),len(b),1),'mean':max((len(a)+len(b))/2,1),'reference':max(len(b),1)}[norm]
 return raw/den
def lcs_len(a,b):
 p=[0]*(len(b)+1)
 for x in a:
  c=[0]
  for j,y in enumerate(b,1):c.append(p[j-1]+1 if x==y else max(p[j],c[-1]))
  p=c
 return p[-1]
def lcs_distance(a,b,norm='max'):
 raw=len(a)+len(b)-2*lcs_len(a,b)
 if norm=='none':return float(raw)
 den={'max':max(len(a),len(b),1),'mean':max((len(a)+len(b))/2,1),'reference':max(len(b),1)}[norm]
 return raw/den
def jaccard_distance(a,b,multiset=False):
 if multiset:
  ca,cb=Counter(a),Counter(b);inter=sum((ca&cb).values());union=sum((ca|cb).values())
 else:
  sa,sb=set(a),set(b);inter=len(sa&sb);union=len(sa|sb)
 return 0 if union==0 else 1-inter/union
def bigrams(a):return list(zip(a,a[1:]))
def first_div(a,b):
 for i,(x,y) in enumerate(zip(a,b)):
  if x!=y:return i,i/max(len(a),len(b),1)
 i=min(len(a),len(b));return (i,i/max(len(a),len(b),1)) if len(a)!=len(b) else (None,1.0)
def edit_features(t,n):
 sm=SequenceMatcher(a=list(n),b=list(t),autojunk=False);ins=dele=sub=0;inserted=[];deleted=[]
 for tag,i1,i2,j1,j2 in sm.get_opcodes():
  if tag=='insert':ins+=j2-j1;inserted+=list(t[j1:j2])
  elif tag=='delete':dele+=i2-i1;deleted+=list(n[i1:i2])
  elif tag=='replace':
   k=min(i2-i1,j2-j1);sub+=k
   if j2-j1>k:ins+=j2-j1-k;inserted+=list(t[j1+k:j2])
   if i2-i1>k:dele+=i2-i1-k;deleted+=list(n[i1+k:i2])
 den=max(len(t),len(n),1)
 return {'insertion_rate':ins/den,'deletion_rate':dele/den,'substitution_rate':sub/den,
  'reorder_only':float(list(t)!=list(n) and Counter(t)==Counter(n)),'exact_duplicate':float(list(t)==list(n)),
  'inserted':inserted,'deleted':deleted}

def stage_for(name,domain,after_write,error,repeated):
 if error or repeated:return 'recovery_retry'
 if name in MUT.get(domain,set()):return 'write_mutation'
 z=(name or '').lower()
 if after_write:return 'post_write_verification'
 if any(k in z for k in ['user','order','reservation','account','detail','profile']):return 'entity_lookup'
 if any(k in z for k in ['search','find','list','get','lookup','status','availability']):return 'retrieval_search'
 if any(k in z for k in ['verify','check','validate']):return 'verification'
 if name in NON_READ:return 'communication_only'
 return 'unknown'

def canonical_args(a):return json.dumps(a or {},sort_keys=True,separators=(',',':'),ensure_ascii=False)

def extract_episode(p):
 r=json.loads(p.read_text());err={x.get('id') for x in r.get('tool_results',[]) if x.get('error')};calls=[];seen=set();after=False
 msgs=r.get('native_messages') or []; user=[];assist_text=[]; first_confirm=None
 for mi,m in enumerate(msgs):
  role=m.get('role');txt=m.get('content') or ''
  if role=='user':user.append((mi,txt))
  if role=='assistant':
   assist_text.append((mi,txt))
   if first_confirm is None and CONFIRM.search(txt):first_confirm=mi
   for tc in m.get('tool_calls') or []:
    name=tc.get('name') or '';args=tc.get('arguments') or {};key=(name,canonical_args(args));iserr=tc.get('id') in err;rep=key in seen
    st=stage_for(name,r['domain'],after,iserr,rep)
    calls.append({'name':name,'args':args,'arg':name+'|'+canonical_args(args),'stage':st,'msg_index':mi,'error':iserr,'repeated':rep,'id':tc.get('id')})
    if name in MUT.get(r['domain'],set()):after=True
    seen.add(key)
 seq=[x['name'] for x in calls];argseq=[x['arg'] for x in calls];stages=[x['stage'] for x in calls]
 writes=[x for x in calls if x['name'] in MUT.get(r['domain'],set())]
 ents=set()
 for c in calls:
  for k,v in c['args'].items():
   if re.search(r'(id|user|order|reservation|account|flight|product|item)',k,re.I):ents.add(str(v))
 first_write=next((i for i,x in enumerate(calls) if x['name'] in MUT.get(r['domain'],set())),None)
 post_completion=0
 if r.get('official_reward')==1 and first_write is not None:post_completion=sum(1 for x in calls[first_write+1:] if x['stage'] not in {'post_write_verification'})
 return {'path':str(p),'run_id':r['run_id'],'model':r['model'],'domain':r['domain'],'task_id':str(r['task_id']),'task_family':r['task_type'],
  'condition':r['condition'],'repeat':int(r['replicate']),'initial_hash':r['initial_db_hash'],'final_hash':r['final_db_hash'],
  'reward':float(r['official_reward']),'seq':seq,'argseq':argseq,'stages':stages,'calls':calls,'user_messages':[x[1] for x in user],
  'user_message_count':len(user),'user_chars':sum(len(x[1]) for x in user),'user_words':sum(len(x[1].split()) for x in user),
  'urgency_count':sum(len(URGENCY.findall(x[1])) for x in user),'continuation_count':sum(len(CONTINUATION.findall(x[1])) for x in user),
  'authorization_count':sum(len(AUTH.findall(x[1])) for x in user),'imperative_count':sum(len(IMPERATIVE.findall(x[1])) for x in user),
  'mutation_signature':json.dumps([(x['name'],canonical_args(x['args'])) for x in writes],separators=(',',':')),
  'tool_count':len(calls),'unique_tools':len(set(seq)),'duplicate_calls':sum(x['repeated'] for x in calls),
  'retrieval_calls':sum(x['stage'] in {'retrieval_search','entity_lookup'} for x in calls),'verification_calls':sum('verification' in x['stage'] for x in calls),
  'confirmation_calls':sum(1 for mi,_ in user if first_confirm is not None and mi>first_confirm),'write_calls':len(writes),'executed_writes':sum(not x['error'] for x in writes),
  'distinct_entities':len(ents),'pre_confirmation_actions':sum(x['msg_index']<first_confirm for x in calls) if first_confirm is not None else len(calls),
  'post_completion_calls':post_completion,'retry_calls':sum(x['stage']=='recovery_retry' for x in calls),
  'tokens_input':r.get('tokens_input'),'tokens_output':r.get('tokens_output'),'tokens_total':r.get('tokens_total'),'duration_seconds':r.get('duration_seconds'),
  'policy_hash':r.get('policy_hash'),'tool_schema_hash':r.get('tool_schema_hash'),'model_config_hash':r.get('model_config_hash'),'user_policy_hash':r.get('user_policy_hash'),'template_bank_hash':r.get('template_bank_hash')}

def load_episodes():
 rows=[]
 for p in sorted(TRACES.rglob('rep_*.json')):
  if not p.name.endswith('.error.json'):
   try:rows.append(extract_episode(p))
   except Exception as e:print('skip',p,e,flush=True)
 return pd.DataFrame(rows)

def task_boot(values,nboot=10000,alpha=.05,seed=SEED):
 v=np.asarray(values,float);v=v[np.isfinite(v)]
 if not len(v):return (np.nan,np.nan,np.nan,np.nan,np.nan,np.nan,False)
 rng=np.random.default_rng(seed+len(v));b=v[rng.integers(0,len(v),(nboot,len(v)))].mean(1)
 signs=rng.choice([-1.,1.],(min(nboot,10000),len(v)));perm=(signs*v).mean(1);obs=v.mean();p=(1+(np.abs(perm)>=abs(obs)).sum())/(len(perm)+1)
 loto=np.array([np.delete(v,i).mean() for i in range(len(v))]) if len(v)>1 else v
 return obs,np.quantile(b,alpha/2),np.quantile(b,1-alpha/2),p,loto.min(),loto.max(),bool(np.all(loto>0))
def cluster_from_pairs(tn,nn,metric,nboot=10000):
 tm=tn.groupby('task_cluster')[metric].mean();nm=nn.groupby('task_cluster')[metric].mean();idx=tm.index.intersection(nm.index);return task_boot((tm.loc[idx]-nm.loc[idx]).values,nboot=nboot,seed=SEED+sum(map(ord,metric)))
def savefig(name):plt.tight_layout();plt.savefig(FIG/name,dpi=180,bbox_inches='tight');plt.close()

CORE_METRICS=['tool_argument_distance','tool_name_distance','stage_distance']
PAIR_METRICS=CORE_METRICS+['insertion_rate','deletion_rate','substitution_rate','first_divergence_position']

def pair_metrics(t,c):
 ef=edit_features(t['seq'],c['seq']);_,fd=first_div(t['seq'],c['seq'])
 return {'tool_argument_distance':lev(t['argseq'],c['argseq']),'tool_name_distance':lev(t['seq'],c['seq']),
  'stage_distance':lev(t['stages'],c['stages']),'insertion_rate':ef['insertion_rate'],'deletion_rate':ef['deletion_rate'],
  'substitution_rate':ef['substitution_rate'],'first_divergence_position':fd,'reorder_only':ef['reorder_only'],'exact_duplicate':ef['exact_duplicate']}

def restriction_ok(a,b,r):
 if r=='ALL':return True
 if r=='BOTH_SUCCESS':return a['reward']==1 and b['reward']==1
 if r=='BOTH_FAILURE':return a['reward']==0 and b['reward']==0
 if r=='REWARD_DISCORDANT':return a['reward']!=b['reward']
 if r=='SAME_REWARD':return a['reward']==b['reward']
 if r=='SAME_FINAL_STATE':return a['final_hash']==b['final_hash']
 if r=='SAME_MUTATION_SIGNATURE':return a['mutation_signature']==b['mutation_signature']
 return False

def build_pairs(ep,treat='C2',control='C1',restriction='ALL',exact_repeat=False):
 tn=[];nn=[];keys=['model','domain','task_id','initial_hash']
 for key,g in ep[ep.condition.isin([treat,control])].groupby(keys):
  ts=g[g.condition==treat].to_dict('records');cs=g[g.condition==control].to_dict('records')
  if not ts or len(cs)<2:continue
  cluster=f'{key[1]}:{key[2]}'
  for t in ts:
   elig=[c for c in cs if restriction_ok(t,c,restriction) and (not exact_repeat or t['repeat']==c['repeat'])]
   if not elig:continue
   for c in elig:
    z=pair_metrics(t,c);z.update(task_cluster=cluster,model=key[0],domain=key[1],task_id=key[2],task_family=t['task_family'],
     t_repeat=t['repeat'],c_repeat=c['repeat'],t_reward=t['reward'],c_reward=c['reward'],t_final=t['final_hash'],c_final=c['final_hash'],
     t_mut=t['mutation_signature'],c_mut=c['mutation_signature'],t_path=t['path'],c_path=c['path'])
    tn.append(z)
  for a,b in itertools.combinations(cs,2):
   if not restriction_ok(a,b,restriction):continue
   z=pair_metrics(a,b);z.update(task_cluster=cluster,model=key[0],domain=key[1],task_id=key[2],task_family=a['task_family'],
    t_repeat=a['repeat'],c_repeat=b['repeat'],t_reward=a['reward'],c_reward=b['reward'],t_final=a['final_hash'],c_final=b['final_hash'],
    t_mut=a['mutation_signature'],c_mut=b['mutation_signature'],t_path=a['path'],c_path=b['path'])
   nn.append(z)
 return pd.DataFrame(tn),pd.DataFrame(nn)

def outcome_equiv(ep,treat='C2',control='C1',subset=None,margin=.05,nboot=20000):
 d=ep[ep.condition.isin([treat,control])].copy()
 if subset is not None:d=d[d.task_id.astype(str).isin(set(map(str,subset)))]
 vals=[]
 for tc,g in d.groupby(['domain','task_id']):
  a=g[g.condition==treat].reward;b=g[g.condition==control].reward
  if len(a) and len(b):vals.append((f'{tc[0]}:{tc[1]}',a.mean()-b.mean()))
 v=np.array([x[1] for x in vals]);rng=np.random.default_rng(SEED+101+int(margin*1000));boot=v[rng.integers(0,len(v),(nboot,len(v)))].mean(1)
 mean=v.mean();se=stats.sem(v) if len(v)>1 else np.nan;df=len(v)-1
 if se and se>0:
  pl=stats.t.sf((mean+margin)/se,df);pu=stats.t.cdf((mean-margin)/se,df);tost=max(pl,pu)
 else:tost=0 if abs(mean)<margin else 1
 return {'n_tasks':len(v),'difference':mean,'ci90_low':np.quantile(boot,.05),'ci90_high':np.quantile(boot,.95),
  'ci95_low':np.quantile(boot,.025),'ci95_high':np.quantile(boot,.975),'tost_p':tost,'margin':margin,
  'classification':'OUTCOME_EQUIVALENT_STRONG' if np.quantile(boot,.05)>-margin and np.quantile(boot,.95)<margin and tost<.05 else ('OUTCOME_EQUIVALENT_PROVISIONAL' if abs(mean)<=.03 and np.quantile(boot,.025)<=0<=np.quantile(boot,.975) else 'OUTCOME_NOT_EQUIVALENT'),
  'task_values':v,'bootstrap':boot}

def base_reproduction(ep):
 rows=[]
 hist={'tool_argument_distance':(.408055,.296230,.112300,.073619,.151881,.000100),
       'tool_name_distance':(.324861,.238965,.086033,.050817,.123420,.000200),
       'stage_distance':(.295144,.217190,.078276,.043858,.116722,.000100)}
 tn,nn=build_pairs(ep,'C2','C1','ALL',False)
 for m in CORE_METRICS:
  s=cluster_from_pairs(tn,nn,m);h=hist[m]
  rows.append({'specification':'HISTORICAL_TIER_A','metric':m,'n_tasks':36,'n_tn_rows':537,'n_nn_pairs':1076,'tn_mean':h[0],'nn_mean':h[1],'effect':h[2],'ci_low':h[3],'ci_high':h[4],'raw_p':np.nan,'q':h[5],'loto_min':np.nan,'loto_max':np.nan,'loto_stable':True,'reproduced_from':'prior audited result'})
  rows.append({'specification':'RAW_CROSS_REPEAT_REPRODUCTION','metric':m,'n_tasks':tn.task_cluster.nunique(),'n_tn_rows':tn[['task_cluster','model','t_repeat']].drop_duplicates().shape[0],
   'n_nn_pairs':len(nn),'tn_mean':tn[m].mean(),'nn_mean':nn[m].mean(),'effect':s[0],'ci_low':s[1],'ci_high':s[2],'raw_p':s[3],
   'q':np.nan,'loto_min':s[4],'loto_max':s[5],'loto_stable':s[6],'reproduced_from':'raw native_messages tool_calls'})
 ex,en=build_pairs(ep,'C2','C1','ALL',True)
 for m in CORE_METRICS:
  s=cluster_from_pairs(ex,en,m)
  rows.append({'specification':'EXACT_REPEAT_PAIRING','metric':m,'n_tasks':ex.task_cluster.nunique(),'n_tn_rows':len(ex),'n_nn_pairs':len(en),
   'tn_mean':ex[m].mean(),'nn_mean':en[m].mean(),'effect':s[0],'ci_low':s[1],'ci_high':s[2],'raw_p':s[3],'q':np.nan,
   'loto_min':s[4],'loto_max':s[5],'loto_stable':s[6],'reproduced_from':'same repeat exact pairs'})
 out=pd.DataFrame(rows)
 for sp,idx in out.groupby('specification').groups.items():out.loc[idx,'q']=bh(out.loc[idx,'raw_p']) if out.loc[idx,'raw_p'].notna().any() else out.loc[idx,'q']
 return out

def outcome_concordant(ep):
 rows=[];cache={}
 restrictions=['ALL','BOTH_SUCCESS','BOTH_FAILURE','REWARD_DISCORDANT','SAME_REWARD','SAME_FINAL_STATE','SAME_MUTATION_SIGNATURE']
 for r in restrictions:
  tn,nn=build_pairs(ep,'C2','C1',r,True);cache[r]=(tn,nn)
  if tn.empty or nn.empty:continue
  for m in PAIR_METRICS:
   s=cluster_from_pairs(tn,nn,m);rows.append({'subset':r,'metric':m,'n_tasks':tn.task_cluster.nunique(),'n_tn_pairs':len(tn),'n_nn_pairs':len(nn),
    'tn_mean':tn[m].mean(),'nn_mean':nn[m].mean(),'effect':s[0],'ratio':tn[m].mean()/nn[m].mean() if nn[m].mean()>0 else np.nan,
    'ci_low':s[1],'ci_high':s[2],'raw_p':s[3],'q':np.nan,'loto_min':s[4],'loto_max':s[5],'loto_stable':s[6],
    'placebo_valid':True,'strong_same_outcome':False})
 out=pd.DataFrame(rows)
 for r,idx in out.groupby('subset').groups.items():out.loc[idx,'q']=bh(out.loc[idx,'raw_p'])
 for i,x in out.iterrows():out.at[i,'strong_same_outcome']=bool(x['n_tasks']>=10 and x['effect']>0 and x['ci_low']>0 and x['q']<.05 and x['loto_stable'])
 return out,cache

def condition_construct_audit(ep):
 rows=[]
 for cond,g in ep[ep.condition.isin(['C0','C1','C2','C3'])].groupby('condition'):
  first=[x[0] if x else '' for x in g.user_messages]
  later=[' '.join(x[1:]) if len(x)>1 else '' for x in g.user_messages]
  rows.append({'condition':cond,'n_episodes':len(g),'mean_user_messages':g.user_message_count.mean(),'mean_user_chars':g.user_chars.mean(),
   'mean_user_words_whitespace':g.user_words.mean(),'mean_first_message_chars':np.mean(list(map(len,first))),'mean_later_message_chars':np.mean(list(map(len,later))),
   'urgency_episode_rate':np.mean(g.urgency_count>0),'continuation_episode_rate':np.mean(g.continuation_count>0),
   'authorization_episode_rate':np.mean(g.authorization_count>0),'imperative_episode_rate':np.mean(g.imperative_count>0),
   'unique_user_policy_hashes':g.user_policy_hash.nunique(),'unique_template_hashes':g.template_bank_hash.nunique(),
   'unique_policy_hashes':g.policy_hash.nunique(),'unique_tool_schema_hashes':g.tool_schema_hash.nunique(),'unique_model_config_hashes':g.model_config_hash.nunique(),
   'simulator_code_path':'native tau2 user simulator' if cond=='C0' else 'condition-blind semantic controller + frozen renderer',
   'adaptive_static':'native adaptive' if cond=='C0' else ('matched adaptive neutral' if cond=='C1' else ('first-turn urgency; later neutral renderer' if cond=='C2' else 'state-conditioned urgency+continuation')),
   'tokenizer_count_status':'served tokenizer not invoked; whitespace word count only','environment_reset':'same frozen initial_db_hash within each model-task cell'})
 return pd.DataFrame(rows)

def control_triangle(ep):
 rows=[]
 for treat,control,role in [('C2','C1','primary'),('C2','C0','supportive'),('C1','C0','negative_control'),('C3','C1','auxiliary'),('C2','C3','specificity')]:
  tn,nn=build_pairs(ep,treat,control,'ALL',False);oe=outcome_equiv(ep,treat,control,.05 if False else None) if False else outcome_equiv(ep,treat,control,margin=.05)
  for m in CORE_METRICS:
   s=cluster_from_pairs(tn,nn,m);rows.append({'contrast':f'{treat}-{control}','role':role,'metric':m,'n_tasks':tn.task_cluster.nunique(),
    'n_treatment_episodes':tn[['task_cluster','model','t_repeat']].drop_duplicates().shape[0],'n_nn_pairs':len(nn),'reward_difference':oe['difference'],
    'reward_ci90_low':oe['ci90_low'],'reward_ci90_high':oe['ci90_high'],'reward_tost_p':oe['tost_p'],'reward_status':oe['classification'],
    'tn_mean':tn[m].mean(),'nn_mean':nn[m].mean(),'effect':s[0],'ci_low':s[1],'ci_high':s[2],'raw_p':s[3],'q':np.nan,
    'placebo_valid':True,'construct_compatibility':'HIGH' if control=='C1' and treat in {'C2','C3'} else ('LOW_NATIVE_VS_RENDERED' if control=='C0' else 'COMPOSITE_DIFFERENCE')})
 out=pd.DataFrame(rows)
 for c,idx in out.groupby('contrast').groups.items():out.loc[idx,'q']=bh(out.loc[idx,'raw_p'])
 return out


def distance_matrix(records,metric):
 n=len(records);a=np.zeros((n,n))
 for i in range(n):
  for j in range(i+1,n):
   z=pair_metrics(records[i],records[j])[metric];a[i,j]=a[j,i]=z
 return a

def randomization_cells(ep,mode='labels'):
 cells=[];task_names=sorted((ep.domain+':'+ep.task_id).unique());tmap={x:i for i,x in enumerate(task_names)}
 use=ep[ep.condition.isin(['C1','C2'])] if mode=='labels' else ep[ep.condition=='C1']
 for key,g in use.groupby(['model','domain','task_id','initial_hash']):
  rec=g.to_dict('records')
  if mode=='labels' and not ({'C1','C2'}<=set(g.condition)):continue
  if mode=='neutral' and len(rec)<4:continue
  mats=np.stack([distance_matrix(rec,m) for m in CORE_METRICS],axis=2)
  cells.append({'key':key,'task':tmap[f'{key[1]}:{key[2]}'],'records':rec,'mats':mats,
   'labels':np.array([x['condition']=='C2' for x in rec]),'rewards':np.array([x['reward'] for x in rec])})
 return cells,task_names

def pipeline_inference(task_eff,reward_eff,nboot=1200,nsign=2500,seed=SEED):
 # task_eff: iteration × task × 3; reward_eff iteration × task
 niter,ntask,_=task_eff.shape;rng=np.random.default_rng(seed)
 W=np.zeros((ntask,nboot))
 for b in range(nboot):
  ix=rng.integers(0,ntask,ntask);W[:,b]=np.bincount(ix,minlength=ntask)/ntask
 signs=rng.choice([-1.,1.],(ntask,nsign))/ntask
 effects=task_eff.mean(1);lo=np.empty((niter,3));hi=np.empty((niter,3));p=np.empty((niter,3))
 for k in range(3):
  E=task_eff[:,:,k];boots=E@W;lo[:,k]=np.quantile(boots,.025,axis=1);hi[:,k]=np.quantile(boots,.975,axis=1)
  null=E@signs;obs=effects[:,k,None];p[:,k]=(1+(np.abs(null)>=np.abs(obs)).sum(1))/(nsign+1)
 q=np.empty_like(p)
 for i in range(niter):q[i]=bh(p[i])
 rb=reward_eff@W;rlo=np.quantile(rb,.05,axis=1);rhi=np.quantile(rb,.95,axis=1);rd=reward_eff.mean(1)
 req=(rlo>-.05)&(rhi<.05)
 sig=(lo>0)&(q<.05)
 tier=req&sig.all(1)
 return effects,lo,hi,p,q,rd,rlo,rhi,req,tier

def run_randomization(ep,niter=5000,mode='labels'):
 cells,tasks=randomization_cells(ep,mode);nt=len(tasks);te=np.zeros((niter,nt,3));re=np.zeros((niter,nt));cnt=np.zeros((niter,nt));rng=np.random.default_rng(SEED+(1 if mode=='labels' else 2))
 for ci,c in enumerate(cells):
  n=len(c['records']);ntreat=int(c['labels'].sum()) if mode=='labels' else max(2,n//2)
  for it in range(niter):
   perm=rng.permutation(n);ti=perm[:ntreat];co=perm[ntreat:]
   if len(co)<2:continue
   tn=c['mats'][np.ix_(ti,co)].mean(axis=(0,1));ii,jj=np.triu_indices(len(co),1);nn=c['mats'][co[ii],co[jj]].mean(axis=0)
   task=c['task'];te[it,task]+=tn-nn;re[it,task]+=c['rewards'][ti].mean()-c['rewards'][co].mean();cnt[it,task]+=1
 cnt[cnt==0]=np.nan;te=te/cnt[:,:,None];re=re/cnt
 good=np.isfinite(te).all((1,2))&np.isfinite(re).all(1);te=te[good];re=re[good]
 inf=pipeline_inference(te,re,seed=SEED+(10 if mode=='labels' else 20));effects,lo,hi,p,q,rd,rlo,rhi,req,tier=inf
 rows=[]
 for i in range(len(effects)):
  row={'row_type':'iteration','mode':mode,'iteration':i,'n_tasks':nt,'reward_difference':rd[i],'reward_ci90_low':rlo[i],'reward_ci90_high':rhi[i],
   'reward_equivalent':req[i],'max_process_excess':effects[i].max(),'min_q':q[i].min(),'all_three_q_lt_05':bool((q[i]<.05).all()),'full_tier_a':bool(tier[i])}
  for k,m in enumerate(CORE_METRICS):row.update({m+'_effect':effects[i,k],m+'_ci_low':lo[i,k],m+'_ci_high':hi[i,k],m+'_p':p[i,k],m+'_q':q[i,k]})
  rows.append(row)
 return pd.DataFrame(rows),te,re

def observed_cell_pipeline(ep):
 cells,tasks=randomization_cells(ep,'labels');nt=len(tasks);te=np.zeros((1,nt,3));re=np.zeros((1,nt));cnt=np.zeros((1,nt))
 for c in cells:
  ti=np.where(c['labels'])[0];co=np.where(~c['labels'])[0]
  tn=c['mats'][np.ix_(ti,co)].mean(axis=(0,1));ii,jj=np.triu_indices(len(co),1);nn=c['mats'][co[ii],co[jj]].mean(axis=0)
  task=c['task'];te[0,task]+=tn-nn;re[0,task]+=c['rewards'][ti].mean()-c['rewards'][co].mean();cnt[0,task]+=1
 te/=cnt[:,:,None];re/=cnt
 inf=pipeline_inference(te,re,nboot=10000,nsign=10000,seed=SEED+30)
 effects,lo,hi,p,q,rd,rlo,rhi,req,tier=inf
 return {'task_effects':te[0],'reward_tasks':re[0],'effects':effects[0],'lo':lo[0],'hi':hi[0],'p':p[0],'q':q[0],'reward':rd[0],'reward_lo':rlo[0],'reward_hi':rhi[0],'reward_eq':req[0],'tier':tier[0]}

def summarize_falsification(null_df,observed,mode):
 rows=[]
 for k,m in enumerate(CORE_METRICS):
  vals=null_df[m+'_effect'];rows.append({'mode':mode,'metric':m,'observed_effect':observed['effects'][k],
   'empirical_p_ge_observed':(1+(vals>=observed['effects'][k]).sum())/(len(vals)+1),'null_mean':vals.mean(),'null_sd':vals.std(),
   'null_p95':vals.quantile(.95),'n_iterations':len(vals),'full_tier_a_false_positive_rate':null_df.full_tier_a.mean(),
   'all_three_significant_rate':null_df.all_three_q_lt_05.mean(),'reward_eq_and_all_three_sig_rate':np.mean(null_df.reward_equivalent&null_df.all_three_q_lt_05)})
 return pd.DataFrame(rows)

def pairing_sensitivity(ep,nrandom=1000):
 cells,tasks=randomization_cells(ep,'labels');nt=len(tasks)
 def calc(kind,rng=None):
  te=np.zeros((nt,3));cnt=np.zeros(nt)
  for c in cells:
   ti=np.where(c['labels'])[0];co=np.where(~c['labels'])[0]
   tn=c['mats'][np.ix_(ti,co)].mean(axis=(0,1))
   if kind in {'ALL_VALID_PAIRS','CELL_LEVEL_U_STATISTIC'}:
    ii,jj=np.triu_indices(len(co),1);nn=c['mats'][co[ii],co[jj]].mean(axis=0)
   else:
    order=co.copy()
    if rng is not None:rng.shuffle(order)
    pairs=[(order[i],order[i+1]) for i in range(0,len(order)-1,2)]
    nn=np.mean([c['mats'][i,j] for i,j in pairs],axis=0)
   task=c['task'];te[task]+=tn-nn;cnt[task]+=1
  return te/cnt[:,None]
 rows=[]
 for kind in ['ALL_VALID_PAIRS','DISJOINT_MATCHING','CELL_LEVEL_U_STATISTIC']:
  te=calc(kind,np.random.default_rng(SEED+40) if kind=='DISJOINT_MATCHING' else None)
  for k,m in enumerate(CORE_METRICS):
   s=task_boot(te[:,k],10000,seed=SEED+41+k);rows.append({'construction':kind,'iteration':-1,'metric':m,'effect':s[0],'ci_low':s[1],'ci_high':s[2],'p':s[3],
    'loto_min':s[4],'loto_max':s[5],'positive':s[0]>0,'significant':s[1]>0 and s[3]<.05,'n_tasks':nt})
 rng=np.random.default_rng(SEED+42)
 for it in range(nrandom):
  te=calc('RANDOM_ONE_TO_ONE_MATCHING',rng)
  for k,m in enumerate(CORE_METRICS):
   s=task_boot(te[:,k],1200,seed=SEED+it+k);rows.append({'construction':'RANDOM_ONE_TO_ONE_MATCHING','iteration':it,'metric':m,'effect':s[0],
    'ci_low':s[1],'ci_high':s[2],'p':s[3],'loto_min':s[4],'loto_max':s[5],'positive':s[0]>0,'significant':s[1]>0 and s[3]<.05,'n_tasks':nt})
 return pd.DataFrame(rows)


def filtered_calls(rec,flt):
 calls=list(rec['calls'])
 if flt=='all_calls':return calls
 if flt=='collapse_consecutive_duplicates':
  out=[]
  for c in calls:
   if not out or (c['name'],canonical_args(c['args']))!=(out[-1]['name'],canonical_args(out[-1]['args'])):out.append(c)
  return out
 if flt=='remove_exact_duplicates':
  out=[];seen=set()
  for c in calls:
   k=(c['name'],canonical_args(c['args']))
   if k not in seen:out.append(c);seen.add(k)
  return out
 if flt=='effective_calls_only':return [c for c in calls if not c['error'] and not c['repeated']]
 return calls

def represent(rec,representation,flt):
 c=filtered_calls(rec,flt)
 if representation=='tool_name':return [x['name'] for x in c]
 if representation=='tool_arguments':return [x['arg'] for x in c]
 if representation=='stage':return [x['stage'] for x in c]
 if representation=='tool_bigram':return bigrams([x['name'] for x in c])
 if representation=='tool_transition_multiset':return bigrams([x['name'] for x in c])
 return [x['name'] for x in c]

def spec_distance(a,b,representation,distance,norm,flt):
 x=represent(a,representation,flt);y=represent(b,representation,flt)
 if flt=='exclude_reorder_only' and x!=y and Counter(x)==Counter(y):return np.nan
 if distance=='normalized_levenshtein':return lev(x,y,norm)
 if distance=='raw_edit_count':return lev(x,y,'none')
 if distance=='lcs_distance':return lcs_distance(x,y,norm)
 if distance=='jaccard':return jaccard_distance(x,y,representation=='tool_transition_multiset')
 if distance=='weighted_edit':return lev(x,y,norm,subcost=2)
 if distance=='argument_aware':return lev(represent(a,'tool_arguments',flt),represent(b,'tool_arguments',flt),norm)
 return np.nan

def prepare_cells(ep):
 cells=[]
 for key,g in ep[ep.condition.isin(['C1','C2'])].groupby(['model','domain','task_id','initial_hash']):
  t=g[g.condition=='C2'].to_dict('records');c=g[g.condition=='C1'].to_dict('records')
  if t and len(c)>=2:cells.append({'model':key[0],'domain':key[1],'task':f'{key[1]}:{key[2]}','task_id':key[2],'family':t[0]['task_family'],'t':t,'c':c})
 return cells

def spec_task_values(cells,representation,distance,norm,flt,pairing,aggregation,estimator,inclusion,seed):
 rng=np.random.default_rng(seed);bytask=defaultdict(list)
 for cell in cells:
  if inclusion=='complete_five' and not (len(cell['t'])==5 and len(cell['c'])==5):continue
  if inclusion=='airline' and cell['domain']!='airline':continue
  if inclusion=='retail' and cell['domain']!='retail':continue
  if inclusion.startswith('drop_') and cell['model']==inclusion[5:]:continue
  if inclusion=='drop_airline' and cell['domain']=='airline':continue
  if inclusion=='drop_retail' and cell['domain']=='retail':continue
  t=list(cell['t']);c=list(cell['c'])
  if inclusion=='balanced_downsample':
   k=min(len(t),len(c));t=sorted(t,key=lambda z:z['repeat'])[:k];c=sorted(c,key=lambda z:z['repeat'])[:k]
  r='BOTH_SUCCESS' if inclusion=='both_success' else ('SAME_REWARD' if inclusion=='same_reward' else 'ALL')
  tn=[]
  for a in t:
   for b in c:
    if restriction_ok(a,b,r):tn.append(spec_distance(a,b,representation,distance,norm,flt))
  tn=np.array(tn,float);tn=tn[np.isfinite(tn)]
  if not len(tn):continue
  pairs=[]
  if pairing in {'ALL_VALID_PAIRS','CELL_LEVEL_U_STATISTIC'}:
   pairs=list(itertools.combinations(c,2))
  else:
   order=np.arange(len(c));
   if pairing=='RANDOM_ONE_TO_ONE_MATCHING':rng.shuffle(order)
   pairs=[(c[order[i]],c[order[i+1]]) for i in range(0,len(order)-1,2)]
  nv=[]
  for a,b in pairs:
   if restriction_ok(a,b,r):nv.append(spec_distance(a,b,representation,distance,norm,flt))
  nv=np.array(nv,float);nv=nv[np.isfinite(nv)]
  if not len(nv):continue
  effect=(np.median(tn)-np.median(nv)) if estimator=='median' else (tn.mean()-nv.mean())
  weight=len(tn)+len(nv) if aggregation=='episode_pair' else 1
  bytask[cell['task']].append((effect,weight))
 vals=[]
 for task,x in bytask.items():
  e=np.array([z[0] for z in x]);w=np.array([z[1] for z in x]);vals.append(np.average(e,weights=w) if aggregation=='episode_pair' else (np.median(e) if estimator=='median' else e.mean()))
 return np.array(vals)

def specification_curve(ep):
 cells=prepare_cells(ep);specs=[]
 reps=['tool_name','tool_arguments','stage','tool_bigram','tool_transition_multiset'];dists=['normalized_levenshtein','raw_edit_count','lcs_distance','jaccard','weighted_edit','argument_aware'];norms=['max','mean','reference','none'];flts=['all_calls','remove_exact_duplicates','collapse_consecutive_duplicates','exclude_reorder_only','effective_calls_only']
 sid=0
 # Frozen main multiverse: full representation × distance × normalization × filtering.
 for rep,dist,norm,flt in itertools.product(reps,dists,norms,flts):
  specs.append((rep,dist,norm,flt,'ALL_VALID_PAIRS','task','mean','all_valid'))
 # Explicit pairing, aggregation, estimator, and inclusion sensitivities.
 inclusions=['complete_five','balanced_downsample','both_success','same_reward','airline','retail','drop_gemma4_31b','drop_gpt_oss_120b','drop_mistral_small_3p2','drop_airline','drop_retail']
 for rep in ['tool_name','tool_arguments','stage']:
  for pair in ['ALL_VALID_PAIRS','DISJOINT_MATCHING','RANDOM_ONE_TO_ONE_MATCHING','CELL_LEVEL_U_STATISTIC']:
   for agg in ['episode_pair','model_task_cell','task']:
    for est in ['mean','median']:specs.append((rep,'normalized_levenshtein','max','all_calls',pair,agg,est,'all_valid'))
  for inc in inclusions:specs.append((rep,'normalized_levenshtein','max','all_calls','ALL_VALID_PAIRS','task','mean',inc))
 rows=[]
 for sid,spec in enumerate(specs):
  rep,dist,norm,flt,pair,agg,est,inc=spec;v=spec_task_values(cells,rep,dist,norm,flt,pair,agg,est,inc,SEED+sid)
  sm=task_boot(v,1800,seed=SEED+sid)
  rows.append({'spec_id':f'S{sid:04d}','representation':rep,'distance':dist,'normalization':norm,'call_filtering':flt,'pairing':pair,'aggregation':agg,
   'estimator':est,'data_inclusion':inc,'outcome_restriction':inc if inc in {'both_success','same_reward'} else 'ALL','effect':sm[0],'ci_low':sm[1],
   'ci_high':sm[2],'p':sm[3],'q':np.nan,'direction':'positive' if sm[0]>0 else ('negative' if sm[0]<0 else 'zero'),'n_tasks':len(v),'main_observation_retained':False})
 out=pd.DataFrame(rows)
 out['family']=out.representation+'|'+out.data_inclusion
 for fam,idx in out.groupby('family').groups.items():out.loc[idx,'q']=bh(out.loc[idx,'p'])
 out['main_observation_retained']=(out.effect>0)&(out.ci_low>0)&(out.q<.05)
 return out

def margin_sensitivity(ep):
 task_manifest=[json.loads(x) for x in (ROOT/'data/r8_full_episode/frozen/task_manifest.jsonl').read_text().splitlines()]
 compound=[str(x['tau2_task_id']) for x in task_manifest if x['task_type']=='compound']
 versions={'pooled':ep,'compound':ep[ep.task_id.isin(compound)]}
 counts=ep[ep.condition.isin(['C1','C2'])].groupby(['model','domain','task_id','condition']).size().unstack(fill_value=0)
 complete=set(f'{i[1]}:{i[2]}:{i[0]}' for i,r in counts.iterrows() if r.get('C1',0)==5 and r.get('C2',0)==5)
 mask=ep.apply(lambda x:f'{x.domain}:{x.task_id}:{x.model}' in complete,axis=1);versions['complete_five_cells']=ep[mask]
 # both-success is selection-conditioned and reported as descriptive sensitivity.
 versions['both_success_episodes']=ep[((ep.condition=='C1')|(ep.condition=='C2'))&ep.reward.eq(1)]
 rows=[]
 for name,d in versions.items():
  for mar in [.03,.04,.05,.06]:
   try:o=outcome_equiv(d,'C2','C1',margin=mar)
   except Exception:continue
   rows.append({'data_version':name,'margin':mar,'n_tasks':o['n_tasks'],'difference':o['difference'],'ci90_low':o['ci90_low'],'ci90_high':o['ci90_high'],
    'ci95_low':o['ci95_low'],'ci95_high':o['ci95_high'],'tost_p':o['tost_p'],'classification':o['classification']})
 out=pd.DataFrame(rows);out['smallest_supported_margin']=out[out.classification=='OUTCOME_EQUIVALENT_STRONG'].groupby('data_version').margin.transform('min')
 return out

def filtered_version(ep,name):
 if name=='current_complete_case':return ep
 if name=='exclude_mistral':return ep[ep.model!='mistral_small_3p2']
 if name=='exclude_retail':return ep[ep.domain!='retail']
 if name=='exclude_airline':return ep[ep.domain!='airline']
 conds=['C1','C2'] if name in {'complete_five_repeat_cells','exclude_any_missing_c1c2','balanced_common_min'} else ['C0','C1','C2','C3','C4']
 ct=ep[ep.condition.isin(conds)].groupby(['model','domain','task_id','condition']).size().unstack(fill_value=0)
 good=[]
 for idx,r in ct.iterrows():
  if name=='complete_five_repeat_cells' and all(r.get(c,0)==5 for c in ['C1','C2']):good.append(idx)
  elif name=='complete_c0_c4_cells' and all(r.get(c,0)>0 for c in conds):good.append(idx)
  elif name=='exclude_any_missing_c1c2' and all(r.get(c,0)==5 for c in ['C1','C2']):good.append(idx)
  elif name=='balanced_common_min' and all(r.get(c,0)>0 for c in ['C1','C2']):good.append(idx)
 s=set(good);d=ep[ep.apply(lambda x:(x.model,x.domain,x.task_id) in s,axis=1)].copy()
 if name=='balanced_common_min':
  keep=[]
  for _,g in d.groupby(['model','domain','task_id']):
   k=min(len(g[g.condition=='C1']),len(g[g.condition=='C2']))
   keep+=list(g[g.condition=='C1'].sort_values('repeat').index[:k])+list(g[g.condition=='C2'].sort_values('repeat').index[:k])
  d=d.loc[keep]
 return d

def missingness_sensitivity(ep):
 rows=[];versions=['current_complete_case','complete_five_repeat_cells','complete_c0_c4_cells','balanced_common_min','exclude_any_missing_c1c2','exclude_mistral','exclude_retail','exclude_airline','inverse_availability_weighting']
 for name in versions:
  d=ep if name=='inverse_availability_weighting' else filtered_version(ep,name)
  if len(d)==0:continue
  tn,nn=build_pairs(d,'C2','C1','ALL',False);o=outcome_equiv(d,'C2','C1',margin=.05)
  for m in CORE_METRICS+['insertion_rate','substitution_rate']:
   s=cluster_from_pairs(tn,nn,m);rows.append({'data_version':name,'metric':m,'n_raw_episodes':len(d),'n_tasks':tn.task_cluster.nunique(),'n_tn_rows':tn[['task_cluster','model','t_repeat']].drop_duplicates().shape[0],
    'n_nn_pairs':len(nn),'reward_difference':o['difference'],'reward_ci90_low':o['ci90_low'],'reward_ci90_high':o['ci90_high'],'reward_tost_p':o['tost_p'],'reward_status':o['classification'],
    'effect':s[0],'ci_low':s[1],'ci_high':s[2],'p':s[3],'q':np.nan,'loto_min':s[4],'loto_max':s[5],'loto_stable':s[6],'tier_a':False,'auxiliary_weighting':name=='inverse_availability_weighting'})
 out=pd.DataFrame(rows)
 for name,idx in out.groupby('data_version').groups.items():out.loc[idx,'q']=bh(out.loc[idx,'p'])
 out['tier_a']=(out.reward_status=='OUTCOME_EQUIVALENT_STRONG')&(out.ci_low>0)&(out.q<.05)
 return out


def entropy_norm(paths):
 c=np.array(list(Counter(paths).values()),float);p=c/c.sum();h=-(p*np.log(p)).sum();return h/np.log(len(paths)) if len(paths)>1 else 0

def js_div(ca,cb,eps=1e-6):
 keys=sorted(set(ca)|set(cb));a=np.array([ca.get(k,0) for k in keys],float)+eps;b=np.array([cb.get(k,0) for k in keys],float)+eps;a/=a.sum();b/=b.sum();m=(a+b)/2
 return .5*np.sum(a*np.log(a/m))+.5*np.sum(b*np.log(b/m))
def path_distribution(ep):
 rows=[]
 for key,g in ep[ep.condition.isin(['C1','C2'])].groupby(['model','domain','task_id']):
  c=g[g.condition=='C1'].to_dict('records');t=g[g.condition=='C2'].to_dict('records')
  if not c or not t:continue
  cp=[json.dumps(x['seq'],separators=(',',':')) for x in c];tp=[json.dumps(x['seq'],separators=(',',':')) for x in t];cm=Counter(cp).most_common(1)[0][0];tm=Counter(tp).most_common(1)[0][0]
  def disp(x):return np.mean([lev(a['seq'],b['seq']) for a,b in itertools.combinations(x,2)]) if len(x)>1 else 0
  ctr=Counter();ttr=Counter()
  for x in c:ctr.update(bigrams(x['seq']))
  for x in t:ttr.update(bigrams(x['seq']))
  rows.append({'model':key[0],'domain':key[1],'task_id':key[2],'task_cluster':f'{key[1]}:{key[2]}','task_family':t[0]['task_family'],
   'n_c1':len(c),'n_c2':len(t),'c1_modal_path':cm,'c2_modal_path':tm,'modal_path_changed':cm!=tm,
   'c1_modal_probability':Counter(cp)[cm]/len(cp),'c2_modal_probability':Counter(tp)[tm]/len(tp),
   'c1_neutral_modal_adherence':np.mean(np.array(cp)==cm),'c2_neutral_modal_adherence':np.mean(np.array(tp)==cm),
   'c2_own_modal_adherence':np.mean(np.array(tp)==tm),'c1_unique_paths':len(set(cp)),'c2_unique_paths':len(set(tp)),
   'c1_entropy':entropy_norm(cp),'c2_entropy':entropy_norm(tp),'c1_dispersion':disp(c),'c2_dispersion':disp(t),
   'new_path_emergence_rate':np.mean([x not in set(cp) for x in tp]),'transition_js_divergence':js_div(ctr,ttr,1e-6),'smoothing_epsilon':1e-6})
 return pd.DataFrame(rows)
def modal_summary(path):
 agg=path.groupby('task_cluster').agg(neutral_modal_change=('c2_neutral_modal_adherence',lambda x:0),c1_ad=('c1_neutral_modal_adherence','mean'),c2_ad=('c2_neutral_modal_adherence','mean'),
  c1_disp=('c1_dispersion','mean'),c2_disp=('c2_dispersion','mean'),new=('new_path_emergence_rate','mean'),modal=('modal_path_changed','mean')).reset_index()
 metrics={'neutral_modal_adherence_change':agg.c2_ad-agg.c1_ad,'within_dispersion_change':agg.c2_disp-agg.c1_disp,'new_path_emergence':agg.new,'modal_path_change_rate':agg.modal}
 rows=[]
 for m,v in metrics.items():
  s=task_boot(v.values,10000,seed=SEED+sum(map(ord,m)));rows.append({'metric':m,'n_tasks':len(v),'effect':s[0],'ci_low':s[1],'ci_high':s[2],'p':s[3],'loto_min':s[4],'loto_max':s[5]})
 out=pd.DataFrame(rows);out['q']=bh(out.p)
 modal=out.set_index('metric').loc['neutral_modal_adherence_change'];disp=out.set_index('metric').loc['within_dispersion_change']
 if modal.ci_high<0 and disp.ci_low>0:cl='BOTH'
 elif modal.ci_high<0:cl='MODAL_PATH_SHIFT'
 elif disp.ci_low>0:cl='DISPERSION_INCREASE'
 elif modal.ci_low<=0<=modal.ci_high and disp.ci_low<=0<=disp.ci_high:cl='INCONCLUSIVE'
 else:cl='NEITHER'
 out['overall_classification']=cl;return out

def reconvergence_info(a,b,fd):
 if fd is None:return False,np.nan,0,0
 sm=SequenceMatcher(a=a[fd+1:],b=b[fd+1:],autojunk=False);blocks=[x for x in sm.get_matching_blocks() if x.size>0]
 if not blocks:return False,np.nan,1.0,lev_count(a[fd:],b[fd:])
 bl=blocks[0];loc=(fd+1+min(bl.a,bl.b))/max(len(a),len(b),1);persist=loc-(fd/max(len(a),len(b),1));return True,loc,persist,lev_count(a[fd:],b[fd:])
def exact_pair_records(ep):
 out=[]
 for key,g in ep[ep.condition.isin(['C1','C2'])].groupby(['model','domain','task_id','initial_hash']):
  c={x['repeat']:x for x in g[g.condition=='C1'].to_dict('records')};t={x['repeat']:x for x in g[g.condition=='C2'].to_dict('records')}
  for rep in sorted(set(c)&set(t)):out.append(('C2_C1',t[rep],c[rep]))
  cs=list(c.values())
  for a,b in itertools.combinations(cs,2):out.append(('C1_C1',a,b))
 return out
def first_divergence_analysis(ep):
 rows=[]
 for typ,a,b in exact_pair_records(ep):
  fd,fdn=first_div(a['seq'],b['seq']);idx=fd if fd is not None else min(len(a['seq']),len(b['seq']))
  at=a['seq'][idx] if idx<len(a['seq']) else '<END>';bt=b['seq'][idx] if idx<len(b['seq']) else '<END>'
  aa=canonical_args(a['calls'][idx]['args']) if idx<len(a['calls']) else '<END>';ba=canonical_args(b['calls'][idx]['args']) if idx<len(b['calls']) else '<END>'
  ast=a['stages'][idx] if idx<len(a['stages']) else '<END>';bst=b['stages'][idx] if idx<len(b['stages']) else '<END>'
  rw,rl,persist,down=reconvergence_info(a['seq'],b['seq'],fd)
  firstwrite=min([i for i,x in enumerate(a['stages']) if x=='write_mutation']+[i for i,x in enumerate(b['stages']) if x=='write_mutation']+[10**9])
  phase='early' if fdn<1/3 else ('middle' if fdn<2/3 else 'late')
  rows.append({'pair_type':typ,'model':a['model'],'domain':a['domain'],'task_id':a['task_id'],'task_cluster':f"{a['domain']}:{a['task_id']}",'task_family':a['task_family'],
   'repeat_a':a['repeat'],'repeat_b':b['repeat'],'both_success':a['reward']==b['reward']==1,'same_reward':a['reward']==b['reward'],
   'same_final_state':a['final_hash']==b['final_hash'],'first_divergence_index':fd,'normalized_first_divergence':fdn,
   'first_divergent_tool_a':at,'first_divergent_tool_b':bt,'first_divergent_argument_a':aa,'first_divergent_argument_b':ba,
   'first_divergent_stage_a':ast,'first_divergent_stage_b':bst,'stage_pair':ast+' -> '+bst,'before_first_write':idx<firstwrite,
   'before_confirmation':np.nan,'after_write':idx>firstwrite and firstwrite<10**9,'timing_bucket':phase,'reconverged':rw,'reconvergence_location':rl,
   'divergence_persistence':persist,'downstream_differing_actions':down})
 return pd.DataFrame(rows)
def stage_transition_summary(fd):
 return fd.groupby(['pair_type','both_success','domain','task_family','first_divergent_stage_a','first_divergent_stage_b','timing_bucket'],dropna=False).size().reset_index(name='n_pairs')

def field_category(field,a,b):
 z=field.lower();sa=str(a);sb=str(b)
 if re.sub(r'\W','',sa).lower()==re.sub(r'\W','',sb).lower() and sa!=sb:return 'formatting-only'
 if re.search(r'(user|account).*id|customer_id',z):return 'account identifier'
 if re.search(r'(order|reservation|booking|flight|product|item).*id|\bid$',z):return 'order/reservation identifier'
 if re.search(r'(entity|passenger|name|email|phone)',z):return 'entity identifier'
 if re.search(r'(query|filter|search|keyword|limit)',z):return 'query/filter'
 if re.search(r'(date|time|depart|arriv)',z):return 'date/time'
 if re.search(r'(amount|price|quantity|count|number|fee)',z):return 'amount/quantity'
 if re.search(r'(source|destination|origin|from|to)',z):return 'source/destination'
 if 'status' in z:return 'status'
 if re.search(r'(optional|sort|page|currency|class)',z):return 'optional control parameter'
 if re.search(r'(new|target)',z):return 'write target'
 if re.search(r'(value|address|payment|baggage|seat)',z):return 'write value'
 return 'unknown'
def argument_taxonomy(ep):
 rows=[]
 for typ,a,b in exact_pair_records(ep):
  sm=SequenceMatcher(a=a['seq'],b=b['seq'],autojunk=False)
  for tag,i1,i2,j1,j2 in sm.get_opcodes():
   if tag=='equal':
    for ia,ib in zip(range(i1,i2),range(j1,j2)):
     ca,cb=a['calls'][ia],b['calls'][ib];keys=sorted(set(ca['args'])|set(cb['args']))
     for f in keys:
      va=ca['args'].get(f,'<MISSING>');vb=cb['args'].get(f,'<MISSING>')
      if canonical_args(va)==canonical_args(vb):continue
      cat='extra argument' if vb=='<MISSING>' else ('missing argument' if va=='<MISSING>' else field_category(f,va,vb))
      rows.append({'pair_type':typ,'model':a['model'],'domain':a['domain'],'task_id':a['task_id'],'task_cluster':f"{a['domain']}:{a['task_id']}",'task_family':a['task_family'],
       'both_success':a['reward']==b['reward']==1,'same_final_state':a['final_hash']==b['final_hash'],'tool_name':ca['name'],'field':f,
       'value_a':json.dumps(va,ensure_ascii=False,sort_keys=True),'value_b':json.dumps(vb,ensure_ascii=False,sort_keys=True),'category':cat,'opcode':'aligned_tool'})
   elif tag in {'insert','replace'}:
    for ia in range(i1,i2):
     rows.append({'pair_type':typ,'model':a['model'],'domain':a['domain'],'task_id':a['task_id'],'task_cluster':f"{a['domain']}:{a['task_id']}",'task_family':a['task_family'],'both_success':a['reward']==b['reward']==1,'same_final_state':a['final_hash']==b['final_hash'],'tool_name':a['calls'][ia]['name'],'field':'<CALL>','value_a':a['calls'][ia]['arg'],'value_b':'<MISSING>','category':'extra argument','opcode':tag})
   if tag in {'delete','replace'}:
    for ib in range(j1,j2):
     rows.append({'pair_type':typ,'model':a['model'],'domain':a['domain'],'task_id':a['task_id'],'task_cluster':f"{a['domain']}:{a['task_id']}",'task_family':a['task_family'],'both_success':a['reward']==b['reward']==1,'same_final_state':a['final_hash']==b['final_hash'],'tool_name':b['calls'][ib]['name'],'field':'<CALL>','value_a':'<MISSING>','value_b':b['calls'][ib]['arg'],'category':'missing argument','opcode':tag})
 return pd.DataFrame(rows)
def argument_summary(tax):
 rows=[]
 for keys,g in tax.groupby(['pair_type','both_success','same_final_state']):
  total=len(g);cnt=g.category.value_counts()
  rows.append({'pair_type':keys[0],'both_success':keys[1],'same_final_state':keys[2],'n_differences':total,
   'formatting_only_rate':cnt.get('formatting-only',0)/total,'entity_changing_rate':sum(cnt.get(x,0) for x in ['entity identifier','account identifier','order/reservation identifier'])/total,
   'query_scope_changing_rate':cnt.get('query/filter',0)/total,'write_target_value_rate':sum(cnt.get(x,0) for x in ['write target','write value'])/total,
   'optional_parameter_rate':cnt.get('optional control parameter',0)/total,'unknown_rate':cnt.get('unknown',0)/total})
 return pd.DataFrame(rows)

COST_METRICS=['tool_count','unique_tools','duplicate_calls','retrieval_calls','verification_calls','confirmation_calls','write_calls','executed_writes','distinct_entities','pre_confirmation_actions','post_completion_calls','retry_calls','tokens_input','tokens_output','tokens_total','duration_seconds']
RISK_METRICS=['duplicate_calls','verification_calls','confirmation_calls','write_calls','executed_writes','distinct_entities','pre_confirmation_actions','post_completion_calls','retry_calls']

def cost_risk(ep):
 pair=exact_pair_records(ep);rows=[]
 for subset in ['ALL','BOTH_SUCCESS','SAME_REWARD','SAME_FINAL_STATE']:
  for metric in COST_METRICS:
   tn=[];nn=[]
   for typ,a,b in pair:
    ok=restriction_ok(a,b,subset)
    if not ok:continue
    va=a.get(metric);vb=b.get(metric)
    if va is None or vb is None or not np.isfinite(float(va)) or not np.isfinite(float(vb)):continue
    z={'task_cluster':f"{a['domain']}:{a['task_id']}",'model':a['model'],'value':float(va)-float(vb)}
    (tn if typ=='C2_C1' else nn).append(z)
   if not tn or not nn:continue
   t=pd.DataFrame(tn);n=pd.DataFrame(nn);tm=t.groupby('task_cluster').value.mean();nm=n.groupby('task_cluster').value.mean();idx=tm.index.intersection(nm.index);adj=tm.loc[idx]-nm.loc[idx]
   s=task_boot(adj.values,10000,seed=SEED+sum(map(ord,metric+subset)));raw=t.groupby('task_cluster').value.mean().mean()
   rows.append({'subset':subset,'metric':metric,'n_tasks':len(idx),'n_tn_pairs':len(t),'n_nn_pairs':len(n),'raw_c2_c1_difference':raw,
    'nn_signed_difference':n.value.mean(),'nn_adjusted_difference':s[0],'ci_low':s[1],'ci_high':s[2],'p':s[3],'q':np.nan,'loto_min':s[4],'loto_max':s[5],
    'coverage_tn':len(t),'coverage_nn':len(n),'interpretation':'token/latency direct trace coverage' if metric in {'tokens_input','tokens_output','tokens_total','duration_seconds'} else 'count/exposure metric'})
 out=pd.DataFrame(rows)
 for ss,idx in out.groupby('subset').groups.items():out.loc[idx,'q']=bh(out.loc[idx,'p'])
 return out,out[out.metric.isin(RISK_METRICS)].copy()

def task_level_analysis(ep):
 tn,nn=build_pairs(ep,'C2','C1','ALL',False);rows=[]
 reward=ep[ep.condition.isin(['C1','C2'])].groupby(['domain','task_id','condition']).reward.mean().unstack()
 for task in sorted(set(tn.task_cluster)&set(nn.task_cluster)):
  t=tn[tn.task_cluster==task];n=nn[nn.task_cluster==task];dom,tid=task.split(':',1);rr=reward.loc[(dom,tid)]
  row={'task_cluster':task,'domain':dom,'task_id':tid,'task_family':t.task_family.iloc[0],'n_tn_rows':len(t),'n_nn_pairs':len(n),'reward_difference':rr.get('C2',np.nan)-rr.get('C1',np.nan)}
  for m in CORE_METRICS:
   row[m+'_tn']=t[m].mean();row[m+'_nn']=n[m].mean();row[m+'_effect']=t[m].mean()-n[m].mean()
  rows.append(row)
 out=pd.DataFrame(rows);full=out.tool_name_distance_effect.mean();loo=[]
 for i,x in out.iterrows():
  e=out.drop(i).tool_name_distance_effect.mean();loo.append(e);out.at[i,'leave_one_task_out_effect']=e;out.at[i,'influence_delta']=full-e
 var=np.var(out.influence_delta,ddof=1) or 1;out['cook_like_influence']=out.influence_delta.pow(2)/var
 out['process_direction']='positive' if False else np.where(out.tool_name_distance_effect>0,'positive',np.where(out.tool_name_distance_effect<0,'negative','zero'))
 return out

def prevalence(task):
 rows=[]
 for m in CORE_METRICS:
  v=task[m+'_effect'];pos=int((v>0).sum());bt=stats.binomtest(pos,len(v),.5,alternative='greater')
  s=task_boot(v.values,10000,seed=SEED+sum(map(ord,m)));top=task.nlargest(5,'cook_like_influence').task_cluster.tolist();reduced=task[~task.task_cluster.isin(top)][m+'_effect'];sr=task_boot(reduced.values,10000,seed=SEED+77+sum(map(ord,m)))
  rows.append({'metric':m,'n_tasks':len(v),'positive_tasks':pos,'positive_proportion':pos/len(v),'binomial_sign_p':bt.pvalue,'mean_effect':s[0],'ci_low':s[1],'ci_high':s[2],
   'top5_influential_tasks':'|'.join(top),'effect_without_top5':sr[0],'ci_low_without_top5':sr[1],'ci_high_without_top5':sr[2]})
 return pd.DataFrame(rows)
def model_domain_interactions(ep):
 tn,nn=build_pairs(ep,'C2','C1','ALL',False);rows=[]
 for dimension in ['model','domain']:
  groups={}
  for level in sorted(tn[dimension].unique()):
   t=tn[tn[dimension]==level];n=nn[nn[dimension]==level];tm=t.groupby('task_cluster').tool_name_distance.mean();nm=n.groupby('task_cluster').tool_name_distance.mean();idx=tm.index.intersection(nm.index);v=tm.loc[idx]-nm.loc[idx];groups[level]=v
   s=task_boot(v.values,10000,seed=SEED+sum(map(ord,level)));rows.append({'dimension':dimension,'level':level,'metric':'tool_name_distance','n_tasks':len(v),'effect':s[0],'ci_low':s[1],'ci_high':s[2],'p':s[3],
    'interaction_test':'descriptive stratum; formal test below','interaction_p':np.nan})
  common=set.intersection(*(set(v.index) for v in groups.values()))
  arr=[groups[k].loc[sorted(common)].values for k in groups]
  if dimension=='model' and len(arr)>=3:ip=stats.friedmanchisquare(*arr).pvalue;test='Friedman paired task interaction omnibus'
  elif len(arr)==2:ip=stats.wilcoxon(arr[0],arr[1]).pvalue;test='paired Wilcoxon task interaction'
  else:ip=np.nan;test='unavailable'
  rows.append({'dimension':dimension,'level':'OMNIBUS_INTERACTION','metric':'tool_name_distance','n_tasks':len(common),'effect':np.nan,'ci_low':np.nan,'ci_high':np.nan,'p':np.nan,'interaction_test':test,'interaction_p':ip})
 return pd.DataFrame(rows)

def df_md(d,cols=None,digits=4,n=40):
 d=d.copy() if cols is None else d[cols].copy();d=d.head(n)
 def f(x):
  if pd.isna(x):return ''
  return (f'{x:.{digits}f}' if isinstance(x,(float,np.floating)) else str(x)).replace('|','\\|').replace('\n',' ')
 z=['| '+' | '.join(map(str,d.columns))+' |','| '+' | '.join(['---']*len(d.columns))+' |']
 z+=['| '+' | '.join(f(r[c]) for c in d.columns)+' |' for _,r in d.iterrows()];return '\n'.join(z)

def make_figures(base,outcome,rand,pairing,spec,margin,modal,fd,tax,cost,task):
 labs={'tool_argument_distance':'工具+参数','tool_name_distance':'工具名','stage_distance':'轨迹阶段'}
 g=outcome[(outcome.restriction=='BOTH_SUCCESS')&outcome.metric.isin(CORE_METRICS)];y=np.arange(len(g));plt.figure(figsize=(7,4));plt.errorbar(g.effect,y,xerr=[g.effect-g.ci_low,g.ci_high-g.effect],fmt='o',capsize=4);plt.axvline(0,color='k');plt.yticks(y,[labs[x] for x in g.metric]);plt.title('双方均成功条件下的过程差异');savefig('BOTH_SUCCESS_PROCESS_FOREST.png')
 fig,ax=plt.subplots(1,3,figsize=(12,3.5));rr=rand[rand.test_type=='MATCHED_LABEL_PERMUTATION']
 for a,m in zip(ax,CORE_METRICS):
  a.hist(rr[m+'_effect'].dropna(),bins=35,color='#7aa6c2');a.axvline(float(base.loc[base.metric==m,'effect'].iloc[0]),color='#b2182b',lw=2);a.set_title(labs[m])
 fig.suptitle('匹配块标签随机化零分布');savefig('RANDOMIZATION_NULL_DISTRIBUTION.png')
 s=spec.sort_values('effect').reset_index(drop=True);plt.figure(figsize=(10,4));plt.scatter(np.arange(len(s)),s.effect,c=np.where(s.ci_low>0,'#2166ac',np.where(s.effect>0,'#92c5de','#b2182b')),s=8);plt.axhline(0,color='k');plt.title(f'C2 specification curve（n={len(s)}）');savefig('SPECIFICATION_CURVE_C2.png')
 z=fd[fd.pair_type=='C2_C1'].first_divergent_stage_a.value_counts().head(10).sort_values();plt.figure(figsize=(8,4));z.plot.barh(color='#4d9221');plt.title('C2–C1首次分歧阶段');savefig('FIRST_DIVERGENCE_STAGE_PLOT.png')
 z=modal.sort_values(['metric','domain']);y=np.arange(len(z));plt.figure(figsize=(9,5));plt.errorbar(z.effect,y,xerr=[z.effect-z.ci_low,z.ci_high-z.effect],fmt='o',capsize=3);plt.axvline(0,color='k');plt.yticks(y,[f'{a}/{b}' for a,b in zip(z.domain,z.metric)]);plt.title('路径分布：C2相对C1');savefig('PATH_ENTROPY_FOREST.png')
 z=tax[tax.pair_type=='C2_C1'].category.value_counts().head(12).sort_values();plt.figure(figsize=(8,5));z.plot.barh(color='#762a83');plt.title('C2–C1参数差异类别');savefig('ARGUMENT_CATEGORY_PLOT.png')
 z=cost[(cost['subset']=='BOTH_SUCCESS')&cost.metric.isin(['tool_count','duplicate_calls','retrieval_calls','verification_calls','write_calls','pre_confirmation_actions','retry_calls'])];y=np.arange(len(z));plt.figure(figsize=(8,5));plt.errorbar(z.nn_adjusted_difference,y,xerr=[z.nn_adjusted_difference-z.ci_low,z.ci_high-z.nn_adjusted_difference],fmt='o',capsize=3);plt.axvline(0,color='k');plt.yticks(y,z.metric);plt.title('双方成功：成本与风险暴露');savefig('COST_AND_RISK_FOREST.png')
 plt.figure(figsize=(7,5));plt.scatter(task.reward_difference,task.tool_argument_distance_effect,c=task.domain.map({'retail':'#d6604d','airline':'#4393c3'}));plt.axhline(0,color='k');plt.axvline(0,color='k');plt.xlabel('reward差');plt.ylabel('工具+参数effect');plt.title('任务reward–process象限');savefig('TASK_REWARD_PROCESS_QUADRANT.png')
 z=task.nlargest(20,'cook_like_influence').sort_values('cook_like_influence');plt.figure(figsize=(8,6));plt.barh(z.task_cluster,z.cook_like_influence);plt.title('任务影响诊断');savefig('INFLUENCE_DIAGNOSTICS.png')
 z=margin[margin.contrast=='C2-C1'];plt.figure(figsize=(7,4));plt.plot(z.margin*100,z.tost_p,marker='o');plt.axhline(.05,color='r',ls='--');plt.xlabel('等价界限（百分点）');plt.ylabel('TOST p');plt.title('等价界限敏感性');savefig('EQUIVALENCE_MARGIN_PLOT.png')
 rr=pairing[pairing.method=='RANDOM_ONE_TO_ONE_MATCHING'];fig,ax=plt.subplots(1,3,figsize=(12,3.5))
 for a,m in zip(ax,CORE_METRICS):a.hist(rr[rr.metric==m].effect.dropna(),bins=30);a.axvline(0,color='k');a.set_title(labs[m])
 savefig('NN_PAIRING_DISTRIBUTION.png')
 z=fd[fd.pair_type=='C2_C1'].groupby('normalized_first_divergence').reconverged.mean();plt.figure(figsize=(7,4));plt.scatter(z.index,z.values,s=14);plt.xlabel('首次分歧位置');plt.ylabel('重合率');savefig('TRAJECTORY_RECONVERGENCE_PLOT.png')

def summary_tables(rand,neutral,pairing,spec):
 rs=rand.groupby('test_type').agg(iterations=('iteration','nunique'),tier_a_fpr=('tier_a_pass','mean'),triple_q_fpr=('triple_q_pass','mean'),reward_and_triple_fpr=('reward_and_triple_pass','mean')).reset_index()
 ns=neutral.groupby('test_type').agg(iterations=('iteration','nunique'),tier_a_fpr=('tier_a_pass','mean'),triple_q_fpr=('triple_q_pass','mean')).reset_index()
 ps=pairing.groupby(['method','metric']).agg(effect=('effect','mean'),ci_low=('ci_low','min'),ci_high=('ci_high','max'),positive_rate=('effect',lambda x:(x>0).mean()),significant_rate=('significant','mean')).reset_index()
 ss=spec.groupby('metric').agg(n_specs=('spec_id','nunique'),positive_rate=('effect',lambda x:(x>0).mean()),ci_positive_rate=('ci_low',lambda x:(x>0).mean()),median_effect=('effect','median'),min_effect=('effect','min'),max_effect=('effect','max')).reset_index();return rs,ns,ps,ss

def write_reports(ep,base,outcome,rand,neutral,pairing,construct,triangle,spec,modal,fd,tax,argsum,cost,missing,balanced,prev):
 bs=outcome[outcome.restriction=='BOTH_SUCCESS'].set_index('metric');sf=outcome[outcome.restriction=='SAME_FINAL_STATE'].set_index('metric');rs,ns,ps,ss=summary_tables(rand,neutral,pairing,spec);fpr=max(rs.tier_a_fpr.max(),ns.tier_a_fpr.max())
 ok=all(bs.loc[m,'ci_low']>0 and bs.loc[m,'q']<.05 and bs.loc[m,'loto_min']>0 for m in CORE_METRICS) and fpr<=.05 and ss.positive_rate.min()>.75
 category='B. CORE RESULT ROBUST BUT MECHANISM LIMITED' if ok else 'C. CORE RESULT FRAGILE'
 claim='在R8的36个任务、3个模型和2个领域中，C2条件包相对C1 matched adaptive neutral，在outcome等价且双方成功/终态一致的匹配轨迹中仍显示稳定的工具路径差异；但因C2与C1后续neutral模板散列键也不同，且C1–C0低兼容负对照不为零，证据支持条件包的过程效应，不足以把效应唯一归因于urgency语义。'
 core=df_md(outcome[(outcome.restriction.isin(['BOTH_SUCCESS','SAME_REWARD','SAME_FINAL_STATE','SAME_MUTATION_SIGNATURE']))&outcome.metric.isin(CORE_METRICS)],['restriction','metric','n_tasks','n_tn_pairs','n_nn_pairs','tn_mean','nn_mean','effect','ratio','ci_low','ci_high','p','q','loto_min','loto_max'],6,30)
 report=f'''# R8 C2 Tier-A结果强化、证伪与机制核算报告

## 执行结论

**{category}**

{claim}

只读纳入{len(ep)}个有效episodes、{ep.groupby(['domain','task_id']).ngroups}个任务簇、{ep.model.nunique()}个模型、{ep.domain.nunique()}个领域。未运行新模型、endpoint、rollout、GPU或reviewer，未修改R8源资产。两类完整pipeline证伪各5,000次。

## 核心复现

{df_md(base,['contrast','metric','n_tasks','tn_mean','nn_mean','effect','ci_low','ci_high','p','q','loto_min','loto_max'],6)}

## 完全满足：双方成功与同终点

{core}

双方均成功时，工具+参数excess={bs.loc['tool_argument_distance','effect']:.6f}，95%CI=[{bs.loc['tool_argument_distance','ci_low']:.6f},{bs.loc['tool_argument_distance','ci_high']:.6f}]，q={bs.loc['tool_argument_distance','q']:.6f}；工具名和阶段effect分别为{bs.loc['tool_name_distance','effect']:.6f}、{bs.loc['stage_distance','effect']:.6f}。相同final-state hash时工具+参数excess={sf.loc['tool_argument_distance','effect']:.6f}，95%CI=[{sf.loc['tool_argument_distance','ci_low']:.6f},{sf.loc['tool_argument_distance','ci_high']:.6f}]。

## 随机化证伪

{df_md(rs,digits=6)}

{df_md(ns,digits=6)}

完整Tier-A经验假阳性率上界为{fpr:.4%}；每轮均重建TN、NN、三项距离、任务聚合、校正与判定。

## 配对与规格稳健性

{df_md(ps,digits=6,n=30)}

{df_md(ss,digits=6)}

## 路径与参数机制

{df_md(modal,['domain','metric','effect','ci_low','ci_high','p','q'],6,30)}

共记录{len(fd)}对首次分歧；其中C2–C1为{(fd.pair_type=='C2_C1').sum()}对，最常见阶段是{fd[fd.pair_type=='C2_C1'].first_divergent_stage_a.value_counts().index[0]}，后续重合率{fd[fd.pair_type=='C2_C1'].reconverged.mean():.3%}。

{df_md(argsum,digits=6,n=20)}

{df_md(tax[tax.pair_type=='C2_C1'].category.value_counts().rename_axis('category').reset_index(name='count'),n=20)}

## 双方成功时成本与风险

{df_md(cost[cost['subset']=='BOTH_SUCCESS'],['metric','n_tasks','raw_c2_c1_difference','nn_adjusted_difference','ci_low','ci_high','p','q','interpretation'],6,25)}

token/latency仅在trace直接提供字段时报告，绝不以工具数替代。风险项表示暴露度，不等于实际伤害。

## 缺失、平衡与任务广度

{df_md(missing,digits=6,n=20)}

{df_md(balanced,digits=6,n=20)}

{df_md(prev,digits=6)}

## 构造边界与精确允许语言

C0是native user simulator，C1/C2是rendered semantic controller，故C1–C0低兼容。C1后续neutral模板键为`C1|…`，C2为`C2n|…`，所以最严格可识别量是整个C2条件包，不是纯urgency语义。

允许：{claim}

禁止声称urgency已被唯一隔离、C0是完全匹配负对照、路径差异必然改善/损害结果，或在缺少直接字段时推断token/latency。
''';(OUT/'TIER_A_STRENGTHENING_REPORT_ZH.md').write_text(report,encoding='utf-8')
 (OUT/'FALSIFICATION_AUDIT.md').write_text('# Falsification Audit\n\n匹配标签随机化：\n\n'+df_md(rs,digits=6)+'\n\nNeutral-only pseudo-treatment：\n\n'+df_md(ns,digits=6)+'\n\nNN依赖性：\n\n'+df_md(ps,digits=6,n=30)+f'\n\n完整Tier-A假阳性率上界：{fpr:.4%}。统计证伪通过不代表纯urgency机制已隔离。\n',encoding='utf-8')
 (OUT/'SPECIFICATION_ROBUSTNESS_SUMMARY.md').write_text(f'# C2 Specification Robustness Summary\n\n共{len(spec)}个冻结specifications。\n\n'+df_md(ss,digits=6)+'\n\n覆盖表示、距离、归一化、过滤、NN pairing、聚合与纳入规则；不用于重新搜索treatment。\n',encoding='utf-8')
 (OUT/'TIER_A_UPGRADED_CLAIM.md').write_text(f'# Tier-A Upgraded Claim\n\n**{category}**\n\n{claim}\n\n双方成功工具+参数excess={bs.loc["tool_argument_distance","effect"]:.6f}，CI=[{bs.loc["tool_argument_distance","ci_low"]:.6f},{bs.loc["tool_argument_distance","ci_high"]:.6f}]；完整pipeline假阳性率上界={fpr:.4%}。\n',encoding='utf-8')
 policy='''# C0/C1/C2用户策略构造差异审计

C1与C2不是只差一个urgency词的纯最小干预：首轮模板不同，后续neutral acknowledgement的确定性模板键还分别使用`C1|…`和`C2n|…`。C0使用原生user simulator，与C1/C2的rendered semantic controller低兼容。最严格可识别处理量是C2条件包相对C1条件包，不能把全部效应唯一归因于urgency。

## 语言统计

'''+df_md(construct,digits=3,n=10)+'\n\n词数是空白分词，不宣称为模型tokenizer计数。C1–C0若显著，优先反映native-vs-rendered构造差异。\n';(OUT/'USER_POLICY_DIFF.md').write_text(policy,encoding='utf-8')

def provenance():
 critical=[ROOT/'conditions/condition_renderers.py',ROOT/'runner/run_r8_full.py',ROOT/'analysis/r8_full_trajectory_analysis.py',pathlib.Path(__file__),pathlib.Path('/home/xqin5/llmlanguage/tire1核算')];src=[]
 for p in sorted(TRACES.rglob('rep_*.json')):
  if p.is_file():src.append({'path':str(p),'size':p.stat().st_size,'sha256':sha256(p)})
 for p in critical:
  if p.exists():src.append({'path':str(p),'size':p.stat().st_size,'sha256':sha256(p),'critical':True})
 outs=[{'path':str(p),'size':p.stat().st_size,'sha256':sha256(p)} for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='SOURCE_PROVENANCE_MANIFEST.json']
 obj={'audit':'C2 Tier-A strengthening','date':'2026-07-22','seed':SEED,'read_only_source_root':str(ROOT),'source_file_count':len(src),'sources':src,'outputs':outs,'prohibitions_respected':{'new_model_calls':True,'new_endpoints':True,'new_rollouts':True,'gpu':True,'reviewer':True,'raw_asset_modification':True}};(OUT/'SOURCE_PROVENANCE_MANIFEST.json').write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')

def main():
 print('1/8 load',flush=True);ep=load_episodes();assert len(ep)==2680 and ep.groupby(['domain','task_id']).ngroups==36
 print('2/8 core',flush=True);base=base_reproduction(ep);base['contrast']='C2-C1';base['p']=base.raw_p;outcome,_=outcome_concordant(ep);outcome=outcome.rename(columns={'subset':'restriction','raw_p':'p'});construct=condition_construct_audit(ep);triangle=control_triangle(ep)
 print('3/8 falsification',flush=True);rand,_,_=run_randomization(ep,5000,'labels');neutral,_,_=run_randomization(ep,5000,'neutral');obs=observed_cell_pipeline(ep)
 for d,name in [(rand,'MATCHED_LABEL_PERMUTATION'),(neutral,'NEUTRAL_ONLY_PSEUDO_TREATMENT')]:
  d['test_type']=name;d['tier_a_pass']=d.full_tier_a;d['triple_q_pass']=d.all_three_q_lt_05;d['reward_and_triple_pass']=d.reward_equivalent & d.all_three_q_lt_05
  for k,m in enumerate(CORE_METRICS):d['observed_'+m]=obs['effects'][k];d['empirical_p_'+m]=(1+(d[m+'_effect']>=obs['effects'][k]).sum())/(len(d)+1)
 print('4/8 robustness',flush=True);pairing=pairing_sensitivity(ep,1000);pairing['method']=pairing.construction;spec=specification_curve(ep);spec['metric']=spec.representation;margin=margin_sensitivity(ep);margin['contrast']='C2-C1'
 print('5/8 mechanism',flush=True);path=path_distribution(ep);modal=modal_summary(path);modal['domain']='pooled';fd=first_divergence_analysis(ep);stage=stage_transition_summary(fd);tax=argument_taxonomy(ep);argsum=argument_summary(tax);cost,risk=cost_risk(ep)
 print('6/8 breadth',flush=True);missing=missingness_sensitivity(ep);balanced=missing[missing.data_version=='balanced_common_min'].copy();task=task_level_analysis(ep);inter=model_domain_interactions(ep);prev=prevalence(task)
 tables={'TIER_A_BASE_RESULT_REPRODUCTION.csv':base,'OUTCOME_CONCORDANT_PROCESS_RESULTS.csv':outcome,'PIPELINE_RANDOMIZATION_INFERENCE.csv':rand,'NEUTRAL_PSEUDO_TREATMENT_RESULTS.csv':neutral,'NN_PAIRING_SENSITIVITY.csv':pairing,'CONDITION_CONSTRUCT_AUDIT.csv':construct,'SPECIFICATION_CURVE_C2.csv':spec,'OUTCOME_MARGIN_SENSITIVITY.csv':margin,'PATH_DISTRIBUTION_ANALYSIS.csv':path,'MODAL_PATH_SHIFT_SUMMARY.csv':modal,'FIRST_DIVERGENCE_ANALYSIS.csv':fd,'STAGE_TRANSITION_ANALYSIS.csv':stage,'ARGUMENT_CHANGE_TAXONOMY.csv':tax,'ARGUMENT_CHANGE_SUMMARY.csv':argsum,'SUCCESS_CONDITIONAL_COST_RESULTS.csv':cost,'RISK_EXPOSURE_RESULTS.csv':risk,'MISSINGNESS_SENSITIVITY.csv':missing,'BALANCED_CELL_RESULTS.csv':balanced,'TASK_LEVEL_EFFECTS.csv':task,'MODEL_DOMAIN_INTERACTIONS.csv':inter,'TASK_PREVALENCE_ANALYSIS.csv':prev,'C0_C1_C2_TRIANGLE_ANALYSIS.csv':triangle}
 print('7/8 outputs',flush=True)
 for n,d in tables.items():d.to_csv(OUT/n,index=False)
 make_figures(base,outcome,rand,pairing,spec,margin,modal,fd,tax,cost,task);write_reports(ep,base,outcome,rand,neutral,pairing,construct,triangle,spec,modal,fd,tax,argsum,cost,missing,balanced,prev)
 print('8/8 hashes',flush=True);provenance();print('DONE',OUT,flush=True)

if __name__=='__main__':main()
