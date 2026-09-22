// MLComputePlan placement report on the EDITED .mlmodelc (PREREG G0(c)). computeplan <model.mlmodelc> <units>
#import <Foundation/Foundation.h>
#import <CoreML/CoreML.h>
int main(int argc, char** argv){@autoreleasepool{
  MLModelConfiguration* cfg=[MLModelConfiguration new]; cfg.computeUnits=(MLComputeUnits)atoi(argv[2]);
  dispatch_semaphore_t sem=dispatch_semaphore_create(0); __block int ne=0,cpu=0,gpu=0,other=0; __block NSMutableDictionary* cpuOps=[NSMutableDictionary new];
  [MLComputePlan loadContentsOfURL:[NSURL fileURLWithPath:@(argv[1])] configuration:cfg completionHandler:^(MLComputePlan* plan, NSError* err){
    if(!plan){printf("PLAN FAIL: %s\n",err.localizedDescription.UTF8String); dispatch_semaphore_signal(sem); return;}
    MLModelStructureProgram* prog=plan.modelStructure.program; MLModelStructureProgramFunction* fn=prog.functions[@"main"];
    for(MLModelStructureProgramOperation* op in fn.block.operations){
      MLComputePlanDeviceUsage* u=[plan computeDeviceUsageForMLProgramOperation:op]; if(!u){other++; continue;}
      id dev=u.preferredComputeDevice;
      if([dev isKindOfClass:[MLNeuralEngineComputeDevice class]]) ne++;
      else if([dev isKindOfClass:[MLGPUComputeDevice class]]) gpu++;
      else { cpu++; NSString* k=op.operatorName; cpuOps[k]=@([cpuOps[k] intValue]+1); }
    }
    dispatch_semaphore_signal(sem); }];
  dispatch_semaphore_wait(sem,DISPATCH_TIME_FOREVER);
  printf("PLACEMENT ops NE=%d CPU=%d GPU=%d unplaced=%d\n",ne,cpu,gpu,other);
  for(NSString* k in cpuOps) printf("  CPU op %s x%d\n",k.UTF8String,[cpuOps[k] intValue]);
  return 0;}}
