export const vertexShader = `void main(){gl_Position=vec4(position,1.);}`;
export const fragmentShader = `
precision highp float;
uniform vec2 resolution;
uniform float time;
uniform float mode;
uniform float strength;
uniform vec3 tint;
uniform vec2 pointer;
float hash(vec3 p){p=fract(p*.3183099+vec3(.1,.2,.3));p*=17.;return fract(p.x*p.y*p.z*(p.x+p.y+p.z));}
float noise(vec3 x){vec3 i=floor(x),f=fract(x);f=f*f*(3.-2.*f);return mix(mix(mix(hash(i),hash(i+vec3(1,0,0)),f.x),mix(hash(i+vec3(0,1,0)),hash(i+vec3(1,1,0)),f.x),f.y),mix(mix(hash(i+vec3(0,0,1)),hash(i+vec3(1,0,1)),f.x),mix(hash(i+vec3(0,1,1)),hash(i+vec3(1,1,1)),f.x),f.y),f.z);}
float fbm(vec3 p){return noise(p)*.57+noise(p*2.03)*.28+noise(p*4.07)*.15;}
void main(){
 vec2 uv=(gl_FragCoord.xy-.5*resolution)/min(resolution.x,resolution.y);
 float r=.30; vec2 p=uv-pointer*.012; float d=length(p);
 vec3 col=vec3(.022,.03,.035);
 float glow=exp(-max(d-r,0.)*16.)*.12;
 col+=tint*glow;
 // Deterministic star field, with subdued twinkling.
 vec2 cell=floor(uv*210.);float star=hash(vec3(cell,8.));
 float dotStar=1.-smoothstep(.03,.14,length(fract(uv*210.)-.5));
 col+=vec3(.55,.65,.7)*dotStar*step(.995,star)*(.55+.3*sin(time*.3+star*80.));
 // Inclined orbital paths and a moving probe.
 vec2 q=mat2(.94,-.342,.342,.94)*p;
 float orbit=length(vec2(q.x,q.y*2.7));
 float ring=exp(-abs(orbit-.46)*650.);
 col+=tint*ring*.22;
 float a=time*.13;vec2 probe=vec2(cos(a)*.46,sin(a)*.46/2.7);
 float beacon=length(q-probe);col+=tint*(exp(-beacon*350.)+exp(-beacon*90.)*.22);
 if(d<r){
  vec3 n=vec3(p/r,sqrt(max(0.,1.-dot(p/r,p/r))));
  float rot=time*.045;vec3 s=vec3(cos(rot)*n.x+sin(rot)*n.z,n.y,-sin(rot)*n.x+cos(rot)*n.z);
  float f=fbm(s*5.+vec3(0,time*.045*strength,0));
  float light=.10+.90*max(0.,dot(n,normalize(vec3(-.8,.6,1.))));
  vec3 surface=tint;
  if(mode<.5){
   float bands=sin(s.y*25.+f*12.+time*.10*strength);
   float wisps=fbm(s*vec3(8.,27.,8.)+f*4.);
   surface=mix(vec3(.24,.10,.035),vec3(1.,.78,.43),smoothstep(-1.,1.,bands*.4+wisps));
  }else if(mode<1.5){
   float interior=sin(s.x*29.+sin(s.y*17.)*3.)*sin(s.y*23.+s.z*12.);
   surface=tint*(.20+.65*smoothstep(.15,.8,interior));
   float scan=exp(-abs(n.y-sin(time*.65*strength)*.85)*85.);
   surface+=vec3(.5,1.,1.)*scan*1.4;
   surface+=tint*.4*pow(abs(sin(s.y*55.)),24.);
  }else if(mode<2.5){
   vec3 grid=s*(23.+strength*4.);vec3 g=fract(grid+sin(grid.yzx*.35+time*.25)*.30)-.5;
   float dots=exp(-dot(g,g)*65.);
   surface=tint*(.12+dots*2.1)+vec3(.45,.25,.75)*f*.3;
  }else if(mode<3.5){
   float flow=sin(s.x*14.+f*13.+time*.18*strength)*cos(s.y*12.+f*8.);
   float strands=pow(1.-abs(flow),18.);
   surface=mix(tint*.12,tint,f)+vec3(.6,.9,.4)*strands*.65;
  }else{
   float terrain=fbm(s*(8.+strength*3.));
   float lat=abs(sin(asin(s.y)*30.));float lon=abs(sin(atan(s.x,s.z)*30.));
   float grid=1.-smoothstep(.02,.055,min(lat,lon));
   surface=tint*(.12+terrain*.55)+tint*grid*.5;
   surface*=.7+.3*smoothstep(.3,.65,terrain);
  }
  float rim=pow(1.-n.z,3.);col=surface*light+tint*rim*.65;
  col*=(1.-smoothstep(r-.002,r,d));
 }
 col+=tint*exp(-abs(d-r)*330.)*.2;
 gl_FragColor=vec4(pow(col,vec3(.9)),1.);
}`;
