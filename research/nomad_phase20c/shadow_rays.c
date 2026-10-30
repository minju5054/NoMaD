/* Union of 1cm Bresenham cells behind occupied depth endpoints. */
#include <stdint.h>
#include <stdlib.h>
void shadow_rays(const int32_t *starts,const int32_t *ends,int count,
                 int width,int height,uint8_t *mask) {
    for(int i=0;i<count;i++) {
        int x=starts[2*i],y=starts[2*i+1],ex=ends[2*i],ey=ends[2*i+1];
        int dx=abs(ex-x),sx=x<ex?1:-1,dy=-abs(ey-y),sy=y<ey?1:-1,error=dx+dy,first=1;
        while(1) {
            if(!first && x>=0 && x<width && y>=0 && y<height)mask[y*width+x]=1;
            if(x==ex && y==ey)break;
            first=0;int twice=2*error;
            if(twice>=dy){error+=dy;x+=sx;}
            if(twice<=dx){error+=dx;y+=sy;}
        }
    }
}
