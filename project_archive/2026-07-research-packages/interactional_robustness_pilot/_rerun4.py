import sys; sys.path.insert(0,"/home/xqin5/llmlanguage/interactional_robustness_pilot")
import csv, json, yaml, copy
import src.model_client as mc
# bump default timeout
_orig=mc.OpenAICompatibleClient.__init__
def patched(self, base_url, api_key="EMPTY", timeout=600):
    _orig(self, base_url, api_key, 600)
mc.OpenAICompatibleClient.__init__=patched
from src.agent_loop import run_agent
from src.utils import load_json, load_yaml
from pathlib import Path

config=load_yaml(Path("config.yaml"))
model_config=load_yaml(Path("model_config_qwen.yaml"))
m=model_config["models"][0]
tasks={t["task_id"]:t for t in load_json(Path("data/base_tasks.json"))}
scripts={(s["task_id"],s["condition_id"]):s for s in load_json(Path("data/condition_scripts.json"))["scripts"]}
seeds=[11,13,17,19,23]

targets=[
 ("C1","repeated_abuse",0,0.0),
 ("C1","repeated_abuse",1,0.0),
 ("C1","repeated_abuse",2,0.0),
 ("C1","praise_affect",2,0.2),
]
fixed={}
for task_id,cond,rep,temp in targets:
    seed=seeds[rep%5]
    rid=f"qwen_t{str(temp).replace('.','p')}_{task_id}_{cond}_r{rep}"
    run_meta={"run_id":rid,"model_alias":"qwen","model_id":m["model_id"],"task_id":task_id,
        "condition_id":cond,"repeat_id":rep,"temperature":temp,
        "seed":seed if m.get("supports_seed") is True else "seed_not_supported","tool_protocol":m.get("tool_protocol")}
    res=run_agent(config,m,tasks[task_id],scripts[(task_id,cond)],run_meta,temp,seed)
    mt=res["metrics"]
    print(rid,"-> err=",repr(mt.get("model_error")),"final_ok=",mt.get("final_state_correct"),"tools=",mt.get("tool_sequence"),"tok=",mt.get("output_tokens"))
    fixed[rid]=mt
json.dump({k:v for k,v in fixed.items()}, open("/tmp/fixed4.json","w"))
print("DONE",len(fixed))
