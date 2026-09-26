// kevd_multi: resident kev-form base, one PRE-BOUND MLModel instance per adapter; a switch is a pointer change.
// Same load recipe and entitlements as mutable/ui/kevd.mm. stdin line protocol, one reply line per command, times in ms (mach clock).
//   LOAD <tag> <adapter.bin|none> -> LOADED <ms>  | LOAD_FAIL <err>     (instantiate + keep)
//   USE <tag>                     -> USED <ms>    | USE_FAIL
//   PREDICT <indir> <out.f16>     -> PRED <ms>                          (current instance)
//   BIND <adapter.bin|none>       -> BOUND <ms>                         (legacy path: re-instantiate into slot "_legacy", then USE it)
//   UNLOAD <tag>                  -> UNLOADED     |  MEM -> MEM <phys_footprint_bytes> <n_instances>  |  QUIT
#import <Foundation/Foundation.h>
#import <CoreML/CoreML.h>
#import <objc/message.h>
#include <cstdio>
#include <string>
#include <mach/mach.h>
#include <mach/mach_time.h>
#include <sys/stat.h>
static double now_ms(){ static mach_timebase_info_data_t tb; if(!tb.denom) mach_timebase_info(&tb); return (double)mach_absolute_time()*tb.numer/tb.denom/1e6; }
static unsigned long long phys(){ task_vm_info_data_t v; mach_msg_type_number_t c=TASK_VM_INFO_COUNT;
  return task_info(mach_task_self(),TASK_VM_INFO,(task_info_t)&v,&c)==KERN_SUCCESS? v.phys_footprint:0; }
static MLMultiArray* rd(NSArray<NSNumber*>* shp, NSString* path){
  NSError* e=nil; MLMultiArray* a=[[MLMultiArray alloc] initWithShape:shp dataType:MLMultiArrayDataTypeFloat16 error:&e];
  size_t n=1; for(NSNumber* s in shp) n*=s.unsignedLongValue; FILE* f=fopen(path.UTF8String,"rb"); if(!f) return nil;
  size_t got=fread(a.dataPointer,2,n,f); fclose(f); return got==n?a:nil; }
static MLModel* load(NSURL* mu, const std::string& ad, NSError** e){
  MLModelConfiguration* cfg=[MLModelConfiguration new]; cfg.computeUnits=MLComputeUnitsCPUAndNeuralEngine;
  if(ad!="none"){ NSDictionary* d=@{@"@model_path/weights/adapter.bin":[NSURL fileURLWithPath:@(ad.c_str())]};
    ((void(*)(id,SEL,id))objc_msgSend)(cfg,NSSelectorFromString(@"setE5rtMutableMILWeightURLs:"),d);}
  return [MLModel modelWithContentsOfURL:mu configuration:cfg error:e]; }
int main(int argc, char** argv){@autoreleasepool{ setvbuf(stdout,NULL,_IONBF,0);
  NSURL* mu=[NSURL fileURLWithPath:@(argv[1])]; NSMutableDictionary<NSString*,MLModel*>* inst=[NSMutableDictionary new]; MLModel* m=nil;
  char line[4096]; printf("READY\n");
  while(fgets(line,sizeof line,stdin)){ @autoreleasepool{
    std::string s(line); while(!s.empty()&&(s.back()=='\n'||s.back()=='\r')) s.pop_back();
    if(s=="QUIT") break;
    if(s=="MEM"){ printf("MEM %llu %lu\n",phys(),(unsigned long)inst.count); continue; }
    if(s.rfind("LOAD ",0)==0){ size_t sp=s.find(' ',5); std::string tag=s.substr(5,sp-5), ad=s.substr(sp+1);
      NSError* e=nil; double t0=now_ms(); MLModel* x=load(mu,ad,&e); double t1=now_ms();
      if(!x){printf("LOAD_FAIL %s\n",e?e.localizedDescription.UTF8String:"?"); continue;} inst[@(tag.c_str())]=x; printf("LOADED %.2f\n",t1-t0); continue; }
    if(s.rfind("USE ",0)==0){ double t0=now_ms(); MLModel* x=inst[@(s.substr(4).c_str())]; double t1=now_ms();
      if(!x){printf("USE_FAIL\n"); continue;} m=x; printf("USED %.4f\n",t1-t0); continue; }
    if(s.rfind("UNLOAD ",0)==0){ NSString* k=@(s.substr(7).c_str()); if(inst[k]==m) m=nil; [inst removeObjectForKey:k]; printf("UNLOADED\n"); continue; }
    if(s.rfind("BIND ",0)==0){ std::string ad=s.substr(5); [inst removeObjectForKey:@"_legacy"]; m=nil;
      NSError* e=nil; double t0=now_ms(); MLModel* x=load(mu,ad,&e); double t1=now_ms();
      if(!x){printf("BIND_FAIL %s\n",e?e.localizedDescription.UTF8String:"?"); continue;} inst[@"_legacy"]=x; m=x; printf("BOUND %.2f\n",t1-t0); continue; }
    if(s.rfind("PREDICT ",0)==0){ if(!m){printf("PRED_FAIL not bound\n"); continue;}
      size_t sp=s.find(' ',8); NSString* ind=@(s.substr(8,sp-8).c_str()); NSString* out=@(s.substr(sp+1).c_str());
      NSDictionary* ins=m.modelDescription.inputDescriptionsByName; NSMutableDictionary* feed=[NSMutableDictionary new]; bool ok=true;
      for(NSString* k in @[@"x",@"cos",@"sin",@"neg"]){ MLMultiArray* a=rd([ins[k] multiArrayConstraint].shape,[ind stringByAppendingFormat:@"/%@.f16",k]); if(!a){ok=false;break;} feed[k]=a; }
      if(!ok){printf("PRED_FAIL bad inputs\n"); continue;}
      NSError* e=nil; double t0=now_ms(); id<MLFeatureProvider> o=[m predictionFromFeatures:[[MLDictionaryFeatureProvider alloc] initWithDictionary:feed error:&e] error:&e]; double t1=now_ms();
      if(!o){printf("PRED_FAIL %s\n",e?e.localizedDescription.UTF8String:"?"); continue;}
      MLMultiArray* y=[[o featureValueForName:@"hs"] multiArrayValue]; FILE* f=fopen(out.UTF8String,"wb"); fwrite(y.dataPointer,2,y.strides[0].unsignedLongValue,f); fclose(f); chmod(out.UTF8String,0644);
      printf("PRED %.3f\n",t1-t0); continue; }
    printf("ERR unknown\n"); } }
  return 0;}}
