"""Hybrid lexical retrieval with exact line citations; no generative model."""
from collections import Counter
from dataclasses import dataclass
import hashlib,math,re
from pathlib import Path
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer,ENGLISH_STOP_WORDS

ROOT=Path(__file__).resolve().parent
STOP=set(ENGLISH_STOP_WORDS)
def tokens(text):return [word for word in re.findall(r'[a-z0-9]+',text.casefold()) if word not in STOP]

@dataclass(frozen=True)
class Chunk:
    source:str
    start_line:int
    end_line:int
    text:str
    content_hash:str

def chunk_file(path,root,window=4,overlap=1):
    if not 0<=overlap<window:raise ValueError('overlap must be smaller than window')
    lines=path.read_text(encoding='utf-8').splitlines()
    # Keep headings/paragraphs coherent and retain exact original line ranges.
    chunks=[];start=0
    while start<len(lines):
        end=min(start+window,len(lines));text='\n'.join(lines[start:end])
        if tokens(text):
            chunks.append(Chunk(path.relative_to(root).as_posix(),start+1,end,text,
                                hashlib.sha256(text.encode()).hexdigest()))
        if end==len(lines):break
        start=end-overlap
    return chunks

class EvidenceSearch:
    def __init__(self,documents=ROOT/'data/docs'):
        root=Path(documents).resolve()
        if not root.is_dir():raise ValueError('Document directory does not exist')
        self.chunks=[]
        for path in sorted(root.rglob('*')):
            if path.suffix.casefold() not in {'.md','.txt'} or not path.is_file():continue
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                raise ValueError('Symlinked documents are not allowed')
            if path.stat().st_size>1024*1024:raise ValueError('Each document must be at most 1 MiB')
            self.chunks.extend(chunk_file(path,root))
        if not self.chunks:raise ValueError('No searchable text documents found')
        self.counts=[Counter(tokens(chunk.text)) for chunk in self.chunks]
        self.lengths=np.array([sum(count.values()) for count in self.counts])
        self.avg_length=float(self.lengths.mean()) or 1
        self.df=Counter(term for count in self.counts for term in count)
        self.vectorizer=TfidfVectorizer(ngram_range=(1,2),stop_words='english',sublinear_tf=True)
        self.matrix=self.vectorizer.fit_transform([chunk.text for chunk in self.chunks])

    def search(self,query,top_k=3):
        if not isinstance(query,str) or not 1<=len(query.strip())<=512:
            raise ValueError('query must contain 1–512 characters')
        if isinstance(top_k,bool) or not isinstance(top_k,int) or not 1<=top_k<=10:
            raise ValueError('top_k must be an integer from 1 to 10')
        terms=set(tokens(query));n=len(self.chunks);bm25=np.zeros(n)
        for term in terms:
            frequency=self.df.get(term,0)
            if frequency==0:continue
            idf=math.log(1+(n-frequency+0.5)/(frequency+0.5))
            for i,count in enumerate(self.counts):
                tf=count.get(term,0);k1=1.5;b=0.75
                bm25[i]+=idf*tf*(k1+1)/(tf+k1*(1-b+b*self.lengths[i]/self.avg_length))
        cosine=(self.matrix@self.vectorizer.transform([query]).T).toarray().ravel()
        # Reciprocal rank fusion combines rankings without treating scores as probabilities.
        scores=np.zeros(n)
        for values in [bm25,cosine]:
            positive=[int(i) for i in np.argsort(-values,kind='stable') if values[i]>0]
            for rank,i in enumerate(positive,1):scores[i]+=1/(60+rank)
        results=[];seen=set()
        for i in np.argsort(-scores,kind='stable'):
            if scores[i]<=0:break
            chunk=self.chunks[int(i)]
            if chunk.content_hash in seen:continue
            seen.add(chunk.content_hash)
            results.append({'source':chunk.source,'start_line':chunk.start_line,'end_line':chunk.end_line,
                            'citation':f'{chunk.source}:L{chunk.start_line}-L{chunk.end_line}',
                            'excerpt':chunk.text,'score':round(float(scores[i]),7),
                            'bm25':round(float(bm25[i]),5),'tfidf_cosine':round(float(cosine[i]),5)})
            if len(results)==top_k:break
        return {'query':query,'results':results,'has_matches':bool(results),
                'note':'Ranked source excerpts, not a generated answer. Scores are not confidence probabilities.'}

    def evaluate(self,queries):
        hits=0;reciprocal=0
        for item in queries:
            results=self.search(item['query'],top_k=3)['results']
            ranks=[i+1 for i,result in enumerate(results) if result['source']==item['relevant_source']]
            if ranks:hits+=1;reciprocal+=1/min(ranks)
        return {'queries':len(queries),'hit_rate_at_3':hits/len(queries) if queries else 0,
                'mrr_at_3':reciprocal/len(queries) if queries else 0,'chunks':len(self.chunks),
                'warning':'Hand-authored queries against fictional documentation. Measures retrieval, not answer correctness.'}
