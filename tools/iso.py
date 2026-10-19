import struct,sys
SEC=2352
class Disc:
    def __init__(s,path): s.d=open(path,'rb').read()
    def sec(s,n): o=n*SEC+16; return s.d[o:o+2048]
    def files(s):
        pvd=s.sec(16); root=pvd[156:190]; out={}
        def walk(lba,ln,path):
            d=b''.join(s.sec(lba+i) for i in range((ln+2047)//2048)); i=0
            while i<len(d):
                l=d[i]
                if l==0: i=((i//2048)+1)*2048; continue
                e=d[i:i+l]; el=struct.unpack('<I',e[2:6])[0]; sz=struct.unpack('<I',e[10:14])[0]; fl=e[25]; nm=e[33:33+e[32]]
                if nm not in (b'\0',b'\1'):
                    n=path+nm.decode('latin1').split(';')[0]
                    if fl&2: walk(el,sz,n+'/')
                    else: out[n]=(el,sz)
                i+=l
        walk(struct.unpack('<I',root[2:6])[0],struct.unpack('<I',root[10:14])[0],'')
        return out
    def read(s,name):
        lba,sz=s.files()[name]
        return b''.join(s.sec(lba+i) for i in range((sz+2047)//2048))[:sz]
if __name__=='__main__':
    d=Disc(sys.argv[1]); import os
    for n in sys.argv[3:]: open(os.path.join(sys.argv[2],n),'wb').write(d.read(n))
