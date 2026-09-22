// Resident-base daemon for the live swap UI. Holds ONE compiled kev-form base; adapters bind by e5rt URL.
//   kevd <model.mlmodelc>        (stdin line protocol, one reply line per command, all times measured)
//   BIND <adapter.bin|none>   -> BOUND <ms>            | BIND_FAIL <error>
//   PREDICT <indir> <out.f16> -> PRED <ms>             (indir holds one record: x/cos/sin/neg .f16 at the model's shapes)
//   QUIT
#import <Foundation/Foundation.h>
#import <CoreML/CoreML.h>
#import <objc/message.h>
#include <cstdio>
#include <string>
#include <mach/mach_time.h>
#include <sys/stat.h>
static double now_ms(){ static mach_timebase_info_data_t tb; if(!tb.denom) mach_timebase_info(&tb); return (double)mach_absolute_time()*tb.numer/tb.denom/1e6; }
static MLMultiArray* rd(NSArray<NSNumber*>* shp, NSString* path){
  NSError* e=nil; MLMultiArray* a=[[MLMultiArray alloc] initWithShape:shp dataType:MLMultiArrayDataTypeFloat16 error:&e];
  size_t n=1; for(NSNumber* s in shp) n*=s.unsignedLongValue; FILE* f=fopen(path.UTF8String,"rb"); if(!f) return nil;
  size_t got=fread(a.dataPointer,2,n,f); fclose(f); return got==n?a:nil; }
int main(int argc, char** argv){@autoreleasepool{ setvbuf(stdout,NULL,_IONBF,0);
  NSURL* mu=[NSURL fileURLWithPath:@(argv[1])]; MLModel* m=nil; char line[4096]; printf("READY\n");
  while(fgets(line,sizeof line,stdin)){ @autoreleasepool{
    std::string s(line); while(!s.empty()&&(s.back()=='\n'||s.back()=='\r')) s.pop_back();
    if(s=="QUIT") break;
    if(s.rfind("BIND ",0)==0){ std::string ad=s.substr(5); m=nil;
      MLModelConfiguration* cfg=[MLModelConfiguration new]; cfg.computeUnits=MLComputeUnitsCPUAndNeuralEngine;
      if(ad!="none"){ NSDictionary* d=@{@"@model_path/weights/adapter.bin":[NSURL fileURLWithPath:@(ad.c_str())]};
        ((void(*)(id,SEL,id))objc_msgSend)(cfg,NSSelectorFromString(@"setE5rtMutableMILWeightURLs:"),d);}
      NSError* e=nil; double t0=now_ms(); m=[MLModel modelWithContentsOfURL:mu configuration:cfg error:&e]; double t1=now_ms();
      if(!m) printf("BIND_FAIL %s\n",e?e.localizedDescription.UTF8String:"?"); else printf("BOUND %.1f\n",t1-t0); continue; }
    if(s.rfind("PREDICT ",0)==0){ if(!m){printf("PRED_FAIL not bound\n"); continue;}
      size_t sp=s.find(' ',8); NSString* ind=@(s.substr(8,sp-8).c_str()); NSString* out=@(s.substr(sp+1).c_str());
      NSDictionary* ins=m.modelDescription.inputDescriptionsByName; NSMutableDictionary* feed=[NSMutableDictionary new]; bool ok=true;
      for(NSString* k in @[@"x",@"cos",@"sin",@"neg"]){ MLMultiArray* a=rd([ins[k] multiArrayConstraint].shape,[ind stringByAppendingFormat:@"/%@.f16",k]); if(!a){ok=false;break;} feed[k]=a; }
      if(!ok){printf("PRED_FAIL bad inputs\n"); continue;}
      NSError* e=nil; double t0=now_ms(); id<MLFeatureProvider> o=[m predictionFromFeatures:[[MLDictionaryFeatureProvider alloc] initWithDictionary:feed error:&e] error:&e]; double t1=now_ms();
      if(!o){printf("PRED_FAIL %s\n",e?e.localizedDescription.UTF8String:"?"); continue;}
      MLMultiArray* y=[[o featureValueForName:@"hs"] multiArrayValue]; FILE* f=fopen(out.UTF8String,"wb"); fwrite(y.dataPointer,2,y.strides[0].unsignedLongValue,f); fclose(f); chmod(out.UTF8String,0644);
      printf("PRED %.2f\n",t1-t0); continue; }
    printf("ERR unknown\n"); } }
  return 0;}}
