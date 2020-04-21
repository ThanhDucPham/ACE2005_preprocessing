# ACE_preprocessing
This is a simple code for preprocessing ACE 2005 corpus for Event Extraction task.  Note that ACE 2005 dataset is not free.

I have some modification from repo : https://github.com/nlpcl-lab/ace2005-preprocessing.git
I don't use PosTag and Dependency parsing.
avoid error 'sentence too long' and > 2 sentences when use Stanford parser

# Some modification on dataset file:
 - ETNew york -> ET new york
 - aig.greenberg -> aig. greenberg
 - (entity tag) he new chairman -> the new chair man
 - (event tag) s->'s
 - (sgm file) .4 % => 4%
# Tool
Download stanford-corenlp model.
```bash
wget http://nlp.stanford.edu/software/stanford-corenlp-full-2018-10-05.zip
unzip stanford-corenlp-full-2018-10-05.zip
```
# Data split: 
The data segmentation is specified in data_list.csv
# Format:
   ## conll format
 I have created some format for many target: </br>
    
     <word> <tab> <tag event for trigger> <tab> <tag Name entity>
 - full form: [tag Name entiy] and [tag event for trigger] are in long format: [BOI-tag]-[Type]:[Sub-type]
 - short form: [tag Name entiy] and [tag event for trigger] are in short format: only [sub-type]
 - without Name Entity:  [word] [tab] [tag event for trigger][\n]
  ## Json format:
```json
[
  {
    "sentence": "He visited all his friends.",
    "tokens": ["He", "visited", "all", "his", "friends", "."],
    "pos-tag": ["PRP", "VBD", "PDT", "PRP$", "NNS", "."],
    "golden-entity-mentions": [
      {
        "text": "He", 
        "entity-type": "PER:Individual",
        "start": 0,
        "end": 0
      },
      {
        "text": "his",
        "entity-type": "PER:Group",
        "start": 3,
        "end": 3
      },
      {
        "text": "all his friends",
        "entity-type": "PER:Group",
        "start": 2,
        "end": 5
      }
    ],
    "golden-event-mentions": [
      {
        "trigger": {
          "text": "visited",
          "start": 1,
          "end": 1
        },
        "arguments": [
          {
            "role": "Entity",
            "entity-type": "PER:Individual",
            "text": "He",
            "start": 0,
            "end": 0
          },
          {
            "role": "Entity",
            "entity-type": "PER:Group",
            "text": "all his friends",
            "start": 2,
            "end": 5
          }
        ],
        "event_type": "Contact:Meet"
      }
    ],
    "parse": "(ROOT\n  (S\n    (NP (PRP He))\n    (VP (VBD visited)\n      (NP (PDT all) (PRP$ his) (NNS friends)))\n    (. .)))"
  }
]
```
  
|          | Documents    |  Sentences   |Event Mentions    | Entity Mentions  |
|-------   |--------------|--------------|----------------  |------------------|
| Test     | 40           | 750          | 424              | 4226             |
| Dev      | 30           | 958          | 505              | 4050             |
| Train    | 529          | 16307        | 4420             | 53045            |
  
  



