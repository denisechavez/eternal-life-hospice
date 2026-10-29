export default function ThankYouReview() {
  const reviewPage = `${import.meta.env.BASE_URL}elh-realtop-thank-you-review.html`;

  return (
    <iframe
      title="Google PPC thank-you page design review for Eternal Life Hospice"
      src={reviewPage}
      className="block h-[100dvh] min-h-[560px] w-full border-0 bg-[#f6f1e8]"
      loading="eager"
      referrerPolicy="no-referrer"
    />
  );
}
