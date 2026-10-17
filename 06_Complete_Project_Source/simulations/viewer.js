/* ASTER-6 offline CAD twin. Matrices are row-major; gl uniforms are transposed. */
(() => {
  'use strict';
  const I=()=>[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1];
  const mul=(a,b)=>Array.from({length:16},(_,i)=>[0,1,2,3].reduce((s,k)=>s+a[4*Math.floor(i/4)+k]*b[4*k+i%4],0));
  const tx=(x=0,y=0,z=0)=>[1,0,0,x,0,1,0,y,0,0,1,z,0,0,0,1];
  function rot(axis,q){let m=I(),c=Math.cos(q),s=Math.sin(q);if(axis==='x'){m[5]=c;m[6]=-s;m[9]=s;m[10]=c;}if(axis==='y'){m[0]=c;m[2]=s;m[8]=-s;m[10]=c;}if(axis==='z'){m[0]=c;m[1]=-s;m[4]=s;m[5]=c;}return m;}
  function fk(q){const g=DATA.config.geometry,l=[0,g.upper_arm_length,g.forearm_length,g.wrist_roll_length,g.wrist_pitch_length,g.tool_length],a=['z','y','y','x','y','x'];let t=tx(0,0,g.shoulder_height),frames={base:I()};for(let j=0;j<6;j++){t=mul(t,rot(a[j],q[j]));frames['j'+(j+1)]=t;t=mul(t,tx(l[j]));}return {frames,tcp:t};}
  const transpose=a=>new Float32Array(Array.from({length:16},(_,i)=>a[(i%4)*4+Math.floor(i/4)]));
  const sub=(a,b)=>a.map((v,i)=>v-b[i]),dot=(a,b)=>a.reduce((s,v,i)=>s+v*b[i],0),cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]],unit=a=>{let n=Math.hypot(...a);return a.map(x=>x/n);};
  function lookAt(eye,target){let z=unit(sub(eye,target)),x=unit(cross([0,0,1],z)),y=cross(z,x);return [x[0],x[1],x[2],-dot(x,eye),y[0],y[1],y[2],-dot(y,eye),z[0],z[1],z[2],-dot(z,eye),0,0,0,1];}
  function perspective(aspect){let f=1/Math.tan(Math.PI/8),n=Math.max(.0001,distance/100),z=20;return [f/aspect,0,0,0,0,f,0,0,0,0,(z+n)/(n-z),2*z*n/(n-z),0,0,-1,0];}
  const canvas=document.querySelector('canvas'),gl=canvas.getContext('webgl',{antialias:true,preserveDrawingBuffer:true});
  if(!gl){document.getElementById('status').textContent='WebGL unavailable in this browser.';return;}
  function shader(type,source){let s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s;}
  let program=gl.createProgram();gl.attachShader(program,shader(gl.VERTEX_SHADER,'attribute vec3 p; attribute vec3 n; uniform mat4 model; uniform mat4 vp; varying vec3 normal; varying vec3 world; void main(){vec4 w=model*vec4(p,1.0);world=w.xyz;normal=mat3(model)*n;gl_Position=vp*w;}'));
  gl.attachShader(program,shader(gl.FRAGMENT_SHADER,'precision mediump float; uniform vec3 color; uniform vec3 eye; uniform float unlit; varying vec3 normal; varying vec3 world; void main(){vec3 n=normalize(normal);vec3 l=normalize(vec3(.4,-.6,1.0));float d=max(0.0,dot(n,l));vec3 v=normalize(eye-world);float s=pow(max(0.0,dot(n,normalize(l+v))),40.0)*.20;vec3 c=color*(.38+.62*d)+s;gl_FragColor=vec4(mix(c,color,unlit),1.0);}'));
  gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(program));gl.useProgram(program);
  const loc=Object.fromEntries(['model','vp','color','eye','unlit'].map(k=>[k,gl.getUniformLocation(program,k)]));
  const pLoc=gl.getAttribLocation(program,'p'),nLoc=gl.getAttribLocation(program,'n');
  function buffer(values){let b=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,b);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(values),gl.STATIC_DRAW);return b;}
  function createMesh(vertices,triangles,color,name='',group='base'){
    const p=[],n=[];for(const face of triangles){let vs=face.map(i=>vertices[i]),normal=unit(cross(sub(vs[1],vs[0]),sub(vs[2],vs[0])));if(!normal.every(Number.isFinite))continue;for(let v of vs){p.push(...v);n.push(...normal);}}
    const lo=[0,1,2].map(i=>Math.min(...vertices.map(v=>v[i]))),hi=[0,1,2].map(i=>Math.max(...vertices.map(v=>v[i]))),center=lo.map((v,i)=>(v+hi[i])/2),radius=Math.hypot(...hi.map((v,i)=>(v-lo[i])/2));
    return {p:buffer(p),n:buffer(n),count:p.length/3,color,name,group,center,radius};
  }
  const color=hex=>[1,3,5].map(i=>parseInt(hex.slice(i,i+2),16)/255);
  const meshes=DATA.mesh.components.map(c=>createMesh(c.vertices.map(v=>v.map(x=>x*.001)),c.triangles,color(c.color),c.name,c.group));
  const cube=createMesh([[-1,-1,-1],[1,-1,-1],[1,1,-1],[-1,1,-1],[-1,-1,1],[1,-1,1],[1,1,1],[-1,1,1]],[[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]],[.95,.59,.17]);
  function draw(mesh,model,col=mesh.color,flat=0,mode=gl.TRIANGLES){gl.uniformMatrix4fv(loc.model,false,transpose(model));gl.uniform3fv(loc.color,col);gl.uniform1f(loc.unlit,flat);gl.bindBuffer(gl.ARRAY_BUFFER,mesh.p);gl.vertexAttribPointer(pLoc,3,gl.FLOAT,false,0,0);gl.enableVertexAttribArray(pLoc);gl.bindBuffer(gl.ARRAY_BUFFER,mesh.n);gl.vertexAttribPointer(nLoc,3,gl.FLOAT,false,0,0);gl.enableVertexAttribArray(nLoc);gl.drawArrays(mode,0,mesh.count);}
  function lineMesh(points,col){return {p:buffer(points.flat()),n:buffer(points.map(()=>[0,0,1]).flat()),count:points.length,color:col};}
  let grid=[];for(let x=-1;x<=1.201;x+=.1){grid.push([x,-.9,-.002],[x,.9,-.002]);grid.push([-.9,x,-.002],[1.2,x,-.002]);}
  const gridMesh=lineMesh(grid,[.14,.24,.31]),path=lineMesh(DATA.trajectory.tcp_m,[.20,.76,.79]);
  let q=DATA.config.home_deg.map(x=>x*Math.PI/180),opening=DATA.config.gripper.max_opening,clock=0,playing=false,last=null,yaw=-1.0,pitch=.42,distance=1.45,pathVisible=true,selected=null;
  const component=document.getElementById('component');
  for(const mesh of [...meshes].sort((a,b)=>a.name.localeCompare(b.name))){const option=document.createElement('option');option.value=mesh.name;option.textContent=mesh.name.replaceAll('_',' ');component.appendChild(option);}
  component.onchange=()=>{selected=meshes.find(m=>m.name===component.value)||null;playing=false;distance=selected?Math.max(.012,selected.radius*3.2):1.45;yaw=-1;pitch=.42;document.getElementById('componentInfo').textContent=selected?selected.name+' · '+selected.group.toUpperCase()+' frame':'54 components · complete assembly';updateControls();};
  function componentModel(model,mesh){let m=model.frames[mesh.group];if(/gripper_(jaw_carriage|finger|contact_pad)/.test(mesh.name)){const sign=mesh.name.endsWith('+1')?1:-1;m=mul(m,tx(0,sign*(opening-DATA.config.gripper.max_opening)/2,0));}return m;}
  const point=(m,p)=>[0,1,2].map(i=>m[4*i]*p[0]+m[4*i+1]*p[1]+m[4*i+2]*p[2]+m[4*i+3]);
  const total=DATA.trajectory.t_s.at(-1),timeline=document.getElementById('timeline'),status=document.getElementById('status');timeline.max=total;
  const angles=document.getElementById('angles');
  const sliders=DATA.config.joint_limits_deg.map((range,j)=>{let row=document.createElement('label');row.innerHTML=`<span>J${j+1}</span><input type="range" min="${range[0]}" max="${range[1]}" step=".1" aria-label="Joint ${j+1}"><output></output>`;angles.appendChild(row);let s=row.querySelector('input');s.oninput=()=>{playing=false;q[j]=+s.value*Math.PI/180;updateControls();};return s;});
  function updateControls(){sliders.forEach((s,j)=>{s.value=q[j]*180/Math.PI;s.nextElementSibling.textContent=(q[j]*180/Math.PI).toFixed(1)+'°';});document.getElementById('grip').value=opening*1000;document.getElementById('gripValue').textContent=(opening*1000).toFixed(0)+' mm';document.getElementById('play').textContent=playing?'Pause demo':'Play demo';}
  document.getElementById('grip').max=opening*1000;document.getElementById('grip').oninput=e=>{playing=false;opening=+e.target.value/1000;updateControls();};
  function sample(t){const times=DATA.trajectory.t_s;let lo=0,hi=times.length-1;while(hi-lo>1){let mid=(lo+hi)>>1;if(times[mid]<=t)lo=mid;else hi=mid;}let u=Math.max(0,Math.min(1,(t-times[lo])/(times[hi]-times[lo])));q=DATA.trajectory.q_rad[lo].map((x,j)=>x+(DATA.trajectory.q_rad[hi][j]-x)*u);opening=DATA.config.gripper.max_opening;for(let e of DATA.trajectory.events)if(e.time_s<=t)opening=e.opening_m;clock=t;timeline.value=t;updateControls();}
  timeline.oninput=()=>{playing=false;sample(+timeline.value);};document.getElementById('play').onclick=()=>{if(clock>=total)sample(0);playing=!playing;updateControls();};
  document.getElementById('reset').onclick=()=>{playing=false;sample(0);};
  for(let name of Object.keys(DATA.config.poses_deg)){let b=document.createElement('button');b.textContent=name[0].toUpperCase()+name.slice(1);b.onclick=()=>{playing=false;q=DATA.config.poses_deg[name].map(x=>x*Math.PI/180);opening=DATA.config.gripper.max_opening;updateControls();status.textContent='Named pose / '+name;};document.getElementById('poses').appendChild(b);}
  document.getElementById('path').onchange=e=>pathVisible=e.target.checked;
  let drag=null;canvas.onpointerdown=e=>{drag=[e.clientX,e.clientY];canvas.setPointerCapture(e.pointerId);};canvas.onpointermove=e=>{if(!drag)return;yaw-=(e.clientX-drag[0])*.006;pitch=Math.min(1.35,Math.max(.08,pitch+(e.clientY-drag[1])*.006));drag=[e.clientX,e.clientY];};canvas.onpointerup=()=>drag=null;canvas.onwheel=e=>{e.preventDefault();distance=Math.max(selected ? .012 : .65,Math.min(4,distance*Math.exp(e.deltaY*.001)));};
  function scaledCube(center,sizes){let m=tx(...center);m[0]=sizes[0];m[5]=sizes[1];m[10]=sizes[2];return m;}
  const pick=fk(DATA.config.poses_deg.pick.map(x=>x*Math.PI/180)).tcp,place=fk(DATA.config.poses_deg.place.map(x=>x*Math.PI/180)).tcp;
  const xyz=t=>[t[3],t[7],t[11]];
  function objectPose(tcp){const released=DATA.trajectory.events.some(e=>e.action==='open'&&e.time_s<=clock),grasped=DATA.trajectory.events.some(e=>e.action==='close'&&e.time_s<=clock);return released?place:grasped?tcp:pick;}
  function objectModel(pose){const scale=[.018,DATA.config.demo.object_width/2,.018],m=pose.slice();for(let row=0;row<3;row++)for(let column=0;column<3;column++)m[4*row+column]*=scale[column];return m;}
  function render(timestamp){if(last!==null&&playing){sample(Math.min(total,clock+(timestamp-last)/1000));if(clock>=total){playing=false;updateControls();}}last=timestamp;const ratio=Math.min(2,window.devicePixelRatio||1),w=Math.floor(canvas.clientWidth*ratio),h=Math.floor(canvas.clientHeight*ratio);if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;}gl.viewport(0,0,w,h);gl.clearColor(.043,.082,.122,1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.enable(gl.DEPTH_TEST);let model=fk(q);const target=selected?point(componentModel(model,selected),selected.center):[.25,0,.36],eye=[target[0]+distance*Math.cos(pitch)*Math.cos(yaw),target[1]+distance*Math.cos(pitch)*Math.sin(yaw),target[2]+distance*Math.sin(pitch)];gl.uniformMatrix4fv(loc.vp,false,transpose(mul(perspective(w/h),lookAt(eye,target))));gl.uniform3fv(loc.eye,eye);if(!selected){draw(gridMesh,I(),gridMesh.color,1,gl.LINES);if(pathVisible)draw(path,I(),path.color,1,gl.LINE_STRIP);}
    for(let mesh of meshes){if(!selected||mesh===selected)draw(mesh,componentModel(model,mesh));}
    if(!selected){
    draw(cube,objectModel(objectPose(model.tcp)));
    for(let pose of [pick,place]){let p=xyz(pose),height=Math.max(.001,p[2]-.018);draw(cube,scaledCube([p[0],p[1],height/2],[.06,.06,height/2]),[.15,.32,.4]);}
    }
    document.getElementById('tcp').textContent=xyz(model.tcp).map(x=>(x*1000).toFixed(1)).join(' / ')+' mm';document.getElementById('time').textContent=clock.toFixed(2)+' / '+total.toFixed(2)+' s';if(playing){let phase=DATA.trajectory.phases.find(p=>clock>=p.start_s&&clock<=p.end_s);status.textContent=phase?.name||'Pick-and-place';}requestAnimationFrame(render);
  }
  window.asterDebug={fk,get q(){return q;},get opening(){return opening;},get selectedComponent(){return selected?.name||null;},get renderedComponentCount(){return selected?1:meshes.length;},get objectPose(){return objectPose(fk(q).tcp).slice();},get objectModel(){return objectModel(objectPose(fk(q).tcp));},sample,meshCount:meshes.length};updateControls();requestAnimationFrame(render);
})();
