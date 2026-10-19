import sys
from PIL import Image
def montage(paths,out,cols=4):
    ims=[Image.open(p) for p in paths]; w=max(i.size[0] for i in ims); h=max(i.size[1] for i in ims)
    rows=(len(ims)+cols-1)//cols; m=Image.new('RGB',(w*cols,h*rows))
    for i,im in enumerate(ims): m.paste(im,((i%cols)*w,(i//cols)*h))
    m.save(out)
if __name__=='__main__': montage(sys.argv[2:],sys.argv[1])
