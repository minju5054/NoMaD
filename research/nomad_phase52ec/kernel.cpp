// Analysis-only acceleration of frozen PP/SP and exact circle/site arc clearance.
// No fast-math; every selected solution is independently checked in Python.
#include <cmath>
#include <algorithm>
#include <vector>
#include <cstdint>
constexpr double PI=3.1415926535897932384626433832795;
static double clip(double v,double a,double b){return std::min(std::max(v,a),b);}
static double wrap(double x){x=std::fmod(x+PI,2*PI);if(x<0)x+=2*PI;return x-PI;}
struct P{double x,y;};
static double norm(P p){return std::sqrt(p.x*p.x+p.y*p.y);}
static P sub(P a,P b){return {a.x-b.x,a.y-b.y};}
static double project(const std::vector<P>& p,const std::vector<double>& s,P q){
 double best=1e300,answer=0;
 for(size_t i=0;i+1<p.size();i++){P d=sub(p[i+1],p[i]),v=sub(q,p[i]);double den=d.x*d.x+d.y*d.y,f=clip((v.x*d.x+v.y*d.y)/den,0,1);P e={v.x-f*d.x,v.y-f*d.y};double r=e.x*e.x+e.y*e.y;
  if(r<best){best=r;answer=s[i]+f*(s[i+1]-s[i]);}}
 return answer;
}
static P at(const std::vector<P>&p,const std::vector<double>&s,double x){
 x=clip(x,0,s.back());size_t i=0;while(i+2<p.size() && s[i+1]<=x)i++;double f=(x-s[i])/(s[i+1]-s[i]);return {p[i].x+f*(p[i+1].x-p[i].x),p[i].y+f*(p[i+1].y-p[i].y)};
}
static double interp(const std::vector<double>&s,const std::vector<double>&v,double x){
 if(x<=s[0])return v[0];if(x>=s.back())return v.back();size_t i=0;while(i+2<s.size()&&s[i+1]<=x)i++;double f=(x-s[i])/(s[i+1]-s[i]);return v[i]+f*(v[i+1]-v[i]);
}
extern "C" int tail_rollout(const double* path,int count,const double* B,const double* vw,double cap,double* poses,double* commands,double* meta){
 std::vector<P> p;for(int i=0;i<count;i++){P q={path[2*i],path[2*i+1]};if(p.empty()||norm(sub(q,p.back()))>1e-12)p.push_back(q);}if(p.size()<2)return -1;
 std::vector<double>s(p.size(),0),k(p.size(),0),vlim(p.size(),.3);
 for(size_t i=1;i<p.size();i++)s[i]=s[i-1]+norm(sub(p[i],p[i-1]));
 if(p.size()>=3){for(size_t i=1;i+1<p.size();i++){P u=sub(p[i],p[i-1]),v=sub(p[i+1],p[i]),w={u.x+v.x,u.y+v.y};double den=std::sqrt(u.x*u.x+u.y*u.y+1e-24)*std::sqrt(v.x*v.x+v.y*v.y+1e-24)*std::sqrt(w.x*w.x+w.y*w.y+1e-24);k[i]=2*(u.x*v.y-u.y*v.x)/den;}k[0]=k[1];k.back()=k[k.size()-2];}
 for(size_t i=0;i<p.size();i++)vlim[i]=std::min(.3,.4/std::max(std::abs(k[i]),1e-15));
 for(int i=int(p.size())-2;i>=0;i--)vlim[i]=std::min(vlim[i],std::sqrt(vlim[i+1]*vlim[i+1]+s[i+1]-s[i]));
 for(size_t i=1;i<p.size();i++)vlim[i]=std::min(vlim[i],std::sqrt(vlim[i-1]*vlim[i-1]+s[i]-s[i-1]));
 double x=B[0],y=B[1],yaw=B[2],v=vw[0],w=vw[1],progress=0,target_yaw=0;int mode=0;double start_s=project(p,s,{x,y});
 for(size_t i=0;i<p.size();i++)if(s[i]>=start_s+.05){target_yaw=std::atan2(p[i].y-y,p[i].x-x);if(std::abs(wrap(target_yaw-yaw))>PI/2)mode=1;break;}
 bool braking=false;int request=-1,brake=-1,endpoint=0;poses[0]=x;poses[1]=y;poses[2]=yaw;
 for(int step=0;step<=216;step++){
  if(step>=144&&!braking){braking=true;request=step;}
  if(step%8==0){
   if(!braking){
    if(mode==2&&std::abs(wrap(target_yaw-yaw))<1e-10)mode=0;
    double projected=project(p,s,{x,y});progress=std::max(progress,projected);P target=at(p,s,std::min(s.back(),progress+.25));P delta={target.x-x,target.y-y};
    double local_y=-std::sin(yaw)*delta.x+std::cos(yaw)*delta.y,den=delta.x*delta.x+delta.y*delta.y,kpp=den>1e-24?2*local_y/den:0;
    if(mode==0&&norm(sub({x,y},p.back()))<=.01){braking=true;endpoint=1;request=step;}
    else {
     if(mode==1&&v<=1e-12)mode=2;
     if(mode==2){v=0;w=clip(wrap(target_yaw-yaw)*9,-.4,.4);}
     else{double floor=mode==1?0:.05,target_v=mode==1?0:clip(interp(s,vlim,projected),.05,.3);double prior=v;
       v=clip(target_v,std::max(floor,prior-.5/9),std::min(.3,prior+.5/9));w=clip(v*kpp,-.4,.4);
       if(cap>=0&&mode==0){v=std::max(prior-.5/9,std::min(v,cap));w=clip(v*kpp,-.4,.4);}}
    }
   }
   if(braking){if(brake<0)brake=step;v=std::max(0.,v-.5/9);w=0;
    if(v<=1e-12){meta[0]=endpoint;meta[1]=request/72.;meta[2]=brake/72.;meta[3]=step/72.;meta[4]=0;meta[5]=0;return step;}}
  }
  if(step==216)break;
  commands[2*step]=v;commands[2*step+1]=w;double turn=w/72,half=turn/2,distance=v/72*(half==0?1:std::sin(half)/half);
  x+=distance*std::cos(yaw+half);y+=distance*std::sin(yaw+half);yaw=wrap(yaw+turn);
  poses[3*(step+1)]=x;poses[3*(step+1)+1]=y;poses[3*(step+1)+2]=yaw;
 }
 return -2;
}
extern "C" double tail_clearance(const double* poses,const double* commands,int steps,const uint8_t* occupied,int ny,int nx,const double* origin,double h){
 const double radius=.09,scan=.165;double best=scan-radius;
 for(int i=0;i<=steps;i++){
  const double *p=poses+3*i;double bound=std::min(std::min(p[0]-origin[0],origin[0]+(nx-1)*h-p[0]),std::min(p[1]-origin[1],origin[1]+(ny-1)*h-p[1]));
  best=std::min(best,.025+bound);
 }
 int intervals=std::max(steps,1);
 for(int i=0;i<intervals;i++){
  const double *a=poses+3*i,*b=steps?poses+3*(i+1):a;
  double v=steps?commands[2*i]:0,w=steps?commands[2*i+1]:0,turn=w/72,r=std::abs(w)>1e-15?v/w:0;
  bool curved=std::abs(turn)>=1e-7&&std::abs(v)>1e-12;
  double cx=a[0]-std::sin(a[2])*r,cy=a[1]+std::cos(a[2])*r,start=std::atan2(a[1]-cy,a[0]-cx);
  double dx=b[0]-a[0],dy=b[1]-a[1],den=dx*dx+dy*dy,sag=std::abs(r)*2*std::pow(std::sin(turn/4),2);
  int x0=std::max(0,int(std::floor((std::min(a[0],b[0])-scan-.001-origin[0])/h))),x1=std::min(nx-1,int(std::ceil((std::max(a[0],b[0])+scan+.001-origin[0])/h)));
  int y0=std::max(0,int(std::floor((std::min(a[1],b[1])-scan-.001-origin[1])/h))),y1=std::min(ny-1,int(std::ceil((std::max(a[1],b[1])+scan+.001-origin[1])/h)));
  for(int y=y0;y<=y1;y++)for(int x=x0;x<=x1;x++)if(occupied[y*nx+x]){
   double sx=origin[0]+x*h,sy=origin[1]+y*h,d;
   if(curved){double angle=std::fmod((std::atan2(sy-cy,sx-cx)-start)*(w>0?1:-1),2*PI);if(angle<0)angle+=2*PI;
    d=angle<=std::abs(turn)+1e-12?std::abs(std::hypot(sx-cx,sy-cy)-std::abs(r)):std::min(std::hypot(sx-a[0],sy-a[1]),std::hypot(sx-b[0],sy-b[1]));}
   else{double f=den>1e-24?clip(((sx-a[0])*dx+(sy-a[1])*dy)/den,0,1):0;d=std::hypot(sx-a[0]-f*dx,sy-a[1]-f*dy)-sag;}
   best=std::min(best,d-radius);
  }
 }
 return best;
}
