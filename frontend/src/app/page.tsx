import HeroSection from "@/components/landingpage/hero-section";
import HowToUseSection from "@/components/landingpage/how-to-use";
import { Navbar } from "@/components/landingpage/navbar";

export default function HomePage() {
  return (
    <>
      <Navbar />
      <HeroSection />
      <HowToUseSection />
    </>
  );
}