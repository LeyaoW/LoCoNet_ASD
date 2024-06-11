import time, os, torch, argparse, warnings, glob, pandas, json

from utils.tools import *
from dlhammer.dlhammer import bootstrap

from dataLoader_multiperson import val_loader
from loconet import loconet

import os
os.environ["CUDA_LAUNCH_BLOCKING"] = "1"

class DataPrep():

    def __init__(self, cfg):
        self.cfg = cfg

    def val_dataloader(self):
        cfg = self.cfg
        loader = val_loader(cfg, trialFileName = cfg.evalTrialAVA, 
                            audioPath     = os.path.join(cfg.audioPathAVA , cfg.evalDataType), \
                            visualPath    = os.path.join(cfg.visualPathAVA, cfg.evalDataType), \
                            num_speakers=cfg.MODEL.NUM_SPEAKERS,
                            )
        
        valLoader = torch.utils.data.DataLoader(loader,
                                                batch_size=cfg.VAL.BATCH_SIZE,
                                                shuffle=False,
                                                num_workers=16)
        return valLoader


def prepare_context_files(cfg):
    path = os.path.join(cfg.DATA.dataPathAVA, "csv")
    # for phase in ["val", "test"]:
    for phase in ["test"]:
        csv_f = f"{phase}_loader.csv"
        csv_orig = f"{phase}_orig.csv"
        entity_f = os.path.join(path, phase + "_entity.json")
        ts_f = os.path.join(path, phase + "_ts.json")
        if os.path.exists(entity_f) and os.path.exists(ts_f):
            continue
        orig_df = pandas.read_csv(os.path.join(path, csv_orig))
        entity_data = {}
        ts_to_entity = {}

        for index, row in orig_df.iterrows():

            entity_id = row['entity_id']
            video_id = row['video_id']
            if row['label'] == "SPEAKING_AUDIBLE":
                label = 1
            else:
                label = 0
            ts = float(row['frame_timestamp'])
            if video_id not in entity_data.keys():
                entity_data[video_id] = {}
            if entity_id not in entity_data[video_id].keys():
                entity_data[video_id][entity_id] = {}
            if ts not in entity_data[video_id][entity_id].keys():
                entity_data[video_id][entity_id][ts] = []

            entity_data[video_id][entity_id][ts] = label

            if video_id not in ts_to_entity.keys():
                ts_to_entity[video_id] = {}
            if ts not in ts_to_entity[video_id].keys():
                ts_to_entity[video_id][ts] = []
            ts_to_entity[video_id][ts].append(entity_id)

        with open(entity_f, "w") as f:
            json.dump(entity_data, f)

        with open(ts_f, "w") as f:
            json.dump(ts_to_entity, f)


def main():
    cfg = bootstrap(print_cfg=False)
    epoch = cfg.RESUME_EPOCH

    warnings.filterwarnings("ignore")

    # form file paths using cfg
    cfg = init_args(cfg)
    data = DataPrep(cfg) 

    prepare_context_files(cfg) # dump data in csv file into the json format

    
    if cfg.downloadAVA == True: 
        # Download csv, video and audio data. Extract features from video and audio
        preprocess_AVA(cfg) # Get clips_audio/video files.
        #quit()
        

    s = loconet(cfg) # create a model object.

    s.loadParameters(cfg.RESUME_PATH)
    mAP = s.evaluate_network(epoch=epoch, loader=data.val_dataloader())
    print(f"evaluate ckpt: {cfg.RESUME_PATH}")
    print(mAP)


if __name__ == '__main__':
    main()
