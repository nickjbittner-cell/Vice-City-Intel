// Secure Buffer publisher. Deploy alongside existing production routes, never replace them.
// Requires VCI_PUBLISH_SECRET and BUFFER_ACCESS_TOKEN in the same runtime.
const VIDEO='https://shorts-renderer-production-c5e7c951.up.railway.app/video/intro.mp4';
const API='https://api.buffer.com';
async function graphql(token,query,variables){
 const r=await fetch(API,{method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:JSON.stringify({query,variables}),signal:AbortSignal.timeout(12000)});
 const body=await r.json();
 if(!r.ok||body.errors?.length)throw new Error('buffer_api_error');
 return body.data;
}
export default async function handler(req,res){
 res.setHeader('Cache-Control','no-store');
 if(req.method==='GET')return res.status(200).json({status:'ready',publishing:false,bufferConfigured:!!process.env.BUFFER_ACCESS_TOKEN});
 if(req.method!=='POST')return res.status(405).json({error:'POST required'});
 if(!process.env.VCI_PUBLISH_SECRET||req.headers.authorization!=='Bearer '+process.env.VCI_PUBLISH_SECRET)return res.status(403).json({error:'unauthorized'});
 const token=process.env.BUFFER_ACCESS_TOKEN;
 if(!token)return res.status(503).json({error:'buffer_token_missing'});
 const {title,description='',videoUrl,confirm,dryRun=true}=req.body||{};
 if(confirm!=='PUBLISH_ONE'||videoUrl!==VIDEO||typeof title!=='string'||title.length<5||title.length>100||typeof description!=='string'||description.length>2000)return res.status(400).json({error:'invalid_publish_request'});
 try{
  const r=await fetch(VIDEO,{method:'HEAD',signal:AbortSignal.timeout(12000)});
  if(!r.ok)return res.status(424).json({error:'video_unavailable',httpStatus:r.status});
  const a=await graphql(token,'query { account { organizations { id } } }');
  let matches=[];
  for(const o of a?.account?.organizations||[]){
   const c=await graphql(token,'query ($input: ChannelsInput!) { channels(input: $input) { id name service } }',{input:{organizationId:o.id}});
   matches.push(...(c?.channels||[]).filter(x=>x.service==='youtube'&&x.name==='ViceCityIntel'));
  }
  if(matches.length!==1)return res.status(409).json({error:'channel_match_count',count:matches.length});
  if(dryRun!==false)return res.status(200).json({status:'validated',channelId:matches[0].id,videoUrl:VIDEO,published:false});
  const mutation='mutation CreatePost($input: CreatePostInput!) { createPost(input: $input) { ... on PostActionSuccess { post { id dueAt status } } ... on MutationError { message } } }';
  const input={text:title+'\\n\\n'+description,channelId:matches[0].id,schedulingType:'automatic',mode:'addToQueue',assets:[{video:{url:VIDEO}}]};
  const result=await graphql(token,mutation,{input});
  if(result?.createPost?.post?.id)return res.status(200).json({published:false,queued:true,postId:result.createPost.post.id,dueAt:result.createPost.post.dueAt||null});
  return res.status(422).json({published:false,queued:false,error:result?.createPost?.message||'buffer_no_post_id'});
 }catch(e){return res.status(502).json({error:String(e.message).slice(0,120),published:false})}
}