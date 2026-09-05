import { useState } from "react";
import "./_group.css";

const reviews = [
  { author:"David Hakobyan", published:"a month ago", text:"Our family is eternally grateful to Eternal Life Hospice team for the compassionate, dignified care they provided. The nurses, aides, social worker, chaplain and physician were kind, attentive, compassionate and always available when we needed them. They treated our loved one and our whole family with genuine care during an incredibly difficult time. I’d recommend them without hesitation." },
  { author:"Mariya Pozikov", published:"a month ago", text:"The nurses sent were so kind and knowledgeable. The entire hospice team really supported us through this tough time. So grateful for their team and all their help." },
  { author:"Brenden Kardash", published:"a month ago", text:"This hospice service is professional and caring. I’d recommend it for anyone who needs it themselves or for their loved ones. Consider using them!" },
  { author:"Annie Ashurov", published:"a month ago", text:"Kind and compassionate team, very organized, and takes the highest of level of care with our loved one that used the service. Thank you!" },
  { author:"Sam Johnson", published:"a month ago", text:"Very happy with the service, they were polite, professional and took good care of my mom." }
];

function sentenceExcerpt(value:string){
  if(value.length<=280)return value;
  const sentences=value.match(/[^.!?]+[.!?]+(?:[”"']+)?|[^.!?]+$/g)||[];
  let excerpt="";
  for(const sentence of sentences){
    const next=(excerpt+sentence).trim();
    if(excerpt&&next.length>280)break;
    excerpt=next;
    if(excerpt.length>=280)break;
  }
  return excerpt&&excerpt.length<value.length?excerpt:value;
}

function ReviewCard({review,index}:{review:typeof reviews[number];index:number}){
  const excerpt=sentenceExcerpt(review.text);
  const [expanded,setExpanded]=useState(false);
  return <article className="review-card">
    <div className="review-card-stars" aria-label="5.0 out of 5 stars">★★★★★</div>
    <blockquote><p className="review-card-text" id={`currentReview${index}`}>{expanded?review.text:excerpt}</p></blockquote>
    {excerpt!==review.text&&<button className="review-expand" type="button" aria-expanded={expanded} aria-controls={`currentReview${index}`} onClick={()=>setExpanded(!expanded)}>{expanded?"Show less":"Read full review"}</button>}
    <div className="review-card-footer"><cite>{review.author}</cite><span className="review-card-meta">Google review · {review.published}</span></div>
  </article>;
}

export function Current(){
  const [more,setMore]=useState(false);
  return <section className="elh-reviews current-reviews" aria-labelledby="currentReviewsTitle">
    <div className="reviews-inner">
      <header className="reviews-head">
        <div className="reviews-eyebrow">Google Reviews</div>
        <h1 className="reviews-title" id="currentReviewsTitle">Kind Words From Our Community</h1>
        <p className="reviews-copy">Recent feedback shared through the Eternal Life Hospice Google Business Profile.</p>
        <div className="reviews-summary"><span className="reviews-summary-stars" aria-label="5.0 out of 5 stars">★★★★★</span><span className="reviews-summary-rating">5.0</span><span className="reviews-summary-count">27 Google reviews</span></div>
      </header>
      <div className="reviews-grid">{reviews.slice(0,3).map((review,index)=><ReviewCard key={review.author} review={review} index={index}/>)}</div>
      {more&&<div className="reviews-grid" style={{marginTop:"1.25rem"}}>{reviews.slice(3,5).map((review,index)=><ReviewCard key={review.author} review={review} index={index+3}/>)}</div>}
      <div className="reviews-actions">
        <button className="reviews-more" type="button" aria-expanded={more} onClick={()=>setMore(!more)}>{more?"Show fewer reviews":"View two more reviews"}</button>
        <a className="reviews-google-link" href="https://maps.google.com/?cid=9771388271577679785" target="_blank" rel="noreferrer">Read all reviews on Google →</a>
      </div>
    </div>
  </section>;
}