// PREREG one_base_two_domains (f23be94a) harness: kev-form base, FOUR inputs per record, adapter by e5rt URL.
//   kev4 <model.mlmodelc> <units> <adapterKey|none> <adapterURL> <indir> <nRec> <out.f16> <tslog>
// indir holds x.f16 [nRec,1,D,1,T], cos.f16/sin.f16 [nRec,1,1,HD,T], neg.f16 [nRec,1,1,T,T], all fp16, consecutive.
// Writes hs blocks at the FULL PADDED stride (strides[0]) and appends to <tslog> one line per event:
//   LOAD <mach_ns_start> <mach_ns_end>      PREDICT <rec> <mach_ns_start> <mach_ns_end>
// (the dispatch reconciliation matches issued predictions 1:1 to ANE intervals by time, loads separately).
#import <Foundation/Foundation.h>
#import <CoreML/CoreML.h>
#import <objc/message.h>
#include <cstdio>
#include <mach/mach_time.h>
static double now_ns(){ static mach_timebase_info_data_t tb; if(!tb.denom) mach_timebase_info(&tb); return (double)mach_absolute_time()*tb.numer/tb.denom; }
static MLMultiArray* mk(NSArray<NSNumber*>* shp, FILE* f, const char* nm, int r){
  NSError* e=nil; MLMultiArray* a=[[MLMultiArray alloc] initWithShape:shp dataType:MLMultiArrayDataTypeFloat16 error:&e];
  size_t n=1; for(NSNumber* s in shp) n*=s.unsignedLongValue;
  if(fread(a.dataPointer,2,n,f)!=n){printf("SHORT READ %s rec %d\n",nm,r); exit(3);} return a; }
int main(int argc, char** argv){@autoreleasepool{ setvbuf(stdout,NULL,_IONBF,0);
  if(argc<9){printf("usage\n"); return 64;}
  NSURL* mu=[NSURL fileURLWithPath:@(argv[1])]; int units=atoi(argv[2]);
  MLModelConfiguration* cfg=[MLModelConfiguration new]; cfg.computeUnits=(MLComputeUnits)units;
  if(strcmp(argv[3],"none")!=0){ NSDictionary* d=@{@(argv[3]):[NSURL fileURLWithPath:@(argv[4])]};
    ((void(*)(id,SEL,id))objc_msgSend)(cfg,NSSelectorFromString(@"setE5rtMutableMILWeightURLs:"),d);}
  FILE* ts=fopen(argv[8],"a");
  NSError* e=nil; double t0=now_ns(); MLModel* m=[MLModel modelWithContentsOfURL:mu configuration:cfg error:&e]; double t1=now_ns();
  fprintf(ts,"LOAD %.0f %.0f\n",t0,t1);
  if(!m){printf("LOAD FAIL: %s\n",e?e.localizedDescription.UTF8String:"?"); fclose(ts); return 1;}
  printf("LOAD_MS %.1f\n",(t1-t0)/1e6);
  NSDictionary* ins=m.modelDescription.inputDescriptionsByName;
  NSArray* sx=[ins[@"x"] multiArrayConstraint].shape, *sc=[ins[@"cos"] multiArrayConstraint].shape, *ss=[ins[@"sin"] multiArrayConstraint].shape, *sn=[ins[@"neg"] multiArrayConstraint].shape;
  NSString* ind=@(argv[5]); int nRec=atoi(argv[6]);
  FILE* fx=fopen([ind stringByAppendingString:@"/x.f16"].UTF8String,"rb"); FILE* fc=fopen([ind stringByAppendingString:@"/cos.f16"].UTF8String,"rb");
  FILE* fs=fopen([ind stringByAppendingString:@"/sin.f16"].UTF8String,"rb"); FILE* fn=fopen([ind stringByAppendingString:@"/neg.f16"].UTF8String,"rb");
  if(!fx||!fc||!fs||!fn){printf("missing input file in %s\n",argv[5]); return 9;}
  FILE* fo=fopen(argv[7],"wb"); if(!fo){printf("no out\n"); return 9;}
  double acc=0;
  for(int r=0;r<nRec;r++){
    MLMultiArray *x=mk(sx,fx,"x",r),*c=mk(sc,fc,"cos",r),*s=mk(ss,fs,"sin",r),*n=mk(sn,fn,"neg",r);
    id<MLFeatureProvider> fp=[[MLDictionaryFeatureProvider alloc] initWithDictionary:@{@"x":x,@"cos":c,@"sin":s,@"neg":n} error:&e];
    double a=now_ns(); id<MLFeatureProvider> o=[m predictionFromFeatures:fp error:&e]; double b=now_ns();
    fprintf(ts,"PREDICT %d %.0f %.0f\n",r,a,b); acc+=(b-a);
    if(!o){printf("PREDICT FAIL rec %d: %s\n",r,e?e.localizedDescription.UTF8String:"?"); fclose(ts); return 2;}
    MLMultiArray* y=[[o featureValueForName:@"hs"] multiArrayValue];
    size_t m2=y.strides[0].unsignedLongValue; fwrite(y.dataPointer,2,m2,fo);
  }
  fclose(fo); fclose(ts); printf("OK %d records  PREDICT_MS_MEAN %.2f\n",nRec,acc/1e6/nRec); return 0;}}
