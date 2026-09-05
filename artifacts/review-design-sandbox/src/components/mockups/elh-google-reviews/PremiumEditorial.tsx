import { useState } from "react";
import "./_group.css";

const reviews = [
  { author:"David Hakobyan", text:"Our family is eternally grateful to Eternal Life Hospice team for the compassionate, dignified care they provided. The nurses, aides, social worker, chaplain and physician were kind, attentive, compassionate and always available when we needed them. They treated our loved one and our whole family with genuine care during an incredibly difficult time. I’d recommend them without hesitation." },
  { author:"Mariya Pozikov", text:"The nurses sent were so kind and knowledgeable. The entire hospice team really supported us through this tough time. So grateful for their team and all their help." },
  { author:"Brenden Kardash", text:"This hospice service is professional and caring. I’d recommend it for anyone who needs it themselves or for their loved ones. Consider using them!" },
  { author:"Annie Ashurov", text:"Kind and compassionate team, very organized, and takes the highest of level of care with our loved one that used the service. Thank you!" },
  { author:"Sam Johnson", text:"Very happy with the service, they were polite, professional and took good care of my mom." }
];

export function PremiumEditorial(){
  const [expanded,setExpanded]=useState(false);
  const [more,setMore]=useState(false);
  const featureExcerpt="Our family is eternally grateful to Eternal Life Hospice team for the compassionate, dignified care they provided. The nurses, aides, social worker, chaplain and physician were kind, attentive, compassionate and always available when we needed them.";
  return <section className="elh-reviews premium-reviews" aria-labelledby="premiumReviewsTitle">
    <div className="premium-inner">
      <header className="premium-top">
        <div>
          <div className="premium-kicker">Words entrusted to us</div>
          <h1 className="premium-title" id="premiumReviewsTitle">Care remembered<br/><em>with gratitude.</em></h1>
        </div>
        <div className="premium-intro">
          Recent reflections shared by families through the Eternal Life Hospice Google Business Profile.
          <div className="premium-trust" aria-label="Rated 5.0 from 27 Google reviews">
            <span className="premium-google" aria-hidden="true">G</span>
            <span className="premium-score">5.0</span>
            <span><span className="premium-stars" aria-hidden="true">★★★★★</span><span className="premium-count">27 verified Google reviews</span></span>
          </div>
        </div>
      </header>
      <div className="editorial-grid">
        <article className="feature-quote">
          <div>
            <div className="premium-stars" aria-label="5.0 out of 5 stars">★★★★★</div>
            <blockquote><p id="premiumFeature">{expanded?reviews[0].text:featureExcerpt}</p></blockquote>
            <button type="button" className="feature-expand" aria-expanded={expanded} aria-controls="premiumFeature" onClick={()=>setExpanded(!expanded)}>{expanded?"Show less":"Read their full reflection"}</button>
          </div>
          <div className="quote-credit"><cite>David Hakobyan</cite><span>Google review · one month ago</span></div>
        </article>
        <div className="side-quotes">
          {reviews.slice(1,3).map(review=><article className="side-quote" key={review.author}>
            <div><div className="mini-stars" aria-label="5.0 out of 5 stars">★★★★★</div><blockquote><p>{review.text}</p></blockquote></div>
            <div><cite>{review.author}</cite><small>Google review · one month ago</small></div>
          </article>)}
        </div>
      </div>
      {more&&<div className="premium-more-grid">{reviews.slice(3).map(review=><article className="premium-more-card" key={review.author}><p>“{review.text}”</p><cite>{review.author} · Google review</cite></article>)}</div>}
      <div className="premium-actions">
        <button type="button" className="premium-more" aria-expanded={more} onClick={()=>setMore(!more)}>{more?"Return to three stories":"Read two more family stories"}</button>
        <a className="premium-link" href="https://maps.google.com/?cid=9771388271577679785" target="_blank" rel="noreferrer">Continue to Google Reviews ↗</a>
      </div>
    </div>
  </section>;
}