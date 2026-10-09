import argparse,json
from pathlib import Path
from engine import EvidenceSearch,ROOT
from api import serve

def main():
    parser=argparse.ArgumentParser(description='Search local Markdown/text documents with line citations')
    parser.add_argument('command',choices=['search','evaluate','serve'])
    parser.add_argument('--query');parser.add_argument('--top-k',type=int,default=3)
    parser.add_argument('--docs',type=Path,default=ROOT/'data/docs')
    parser.add_argument('--port',type=int,default=8002)
    args=parser.parse_args();engine=EvidenceSearch(args.docs)
    if args.command=='serve':serve(lambda body:engine.search(body.get('query'),body.get('top_k',3)),args.port)
    elif args.command=='search':print(json.dumps(engine.search(args.query,args.top_k),indent=2))
    else:
        report=engine.evaluate(json.loads((ROOT/'data/queries.json').read_text()))
        out=ROOT/'reports/evaluation.json';out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
