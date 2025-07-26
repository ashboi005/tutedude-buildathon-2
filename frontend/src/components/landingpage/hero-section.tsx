import { Button } from "@/components/ui/button"
import Image from "next/image"

export default function HeroSection() {
  return (
    <section className="px-4 py-16 md:py-24 lg:py-32">
      <div className="container mx-auto max-w-7xl">
        <div className="grid gap-12 lg:grid-cols-2 lg:gap-16 items-center">
          {/* Content */}
          <div className="space-y-8">
            <div className="space-y-6">
              <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-5xl md:text-6xl lg:text-7xl">
                <span className="text-[#e53935]">Ustaad</span>Cart
              </h1>
              <h2 className="text-xl md:text-2xl lg:text-3xl font-semibold text-gray-700 leading-relaxed">
                Connecting Indian Street Vendors with Wholesale Suppliers
              </h2>
              <p className="text-lg md:text-xl text-gray-600 leading-relaxed max-w-2xl">
                Transform your business with India's most trusted B2B platform. Get access to verified suppliers, bulk
                discounts, flexible payment options, and real-time order tracking - all designed specifically for street
                vendors and small businesses.
              </p>
            </div>

            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row gap-4">
              <Button
                size="lg"
                className="bg-[#e53935] hover:bg-[#d32f2f] text-white px-8 py-4 text-lg font-semibold rounded-xl h-auto"
              >
                Get Started Free
              </Button>
              <Button
                variant="outline"
                size="lg"
                className="border-[#e53935] text-[#e53935] hover:bg-[#e53935] hover:text-white px-8 py-4 text-lg font-semibold rounded-xl h-auto bg-transparent"
              >
                How it Works
              </Button>
            </div>
          </div>

          {/* Illustration */}
          <div className="flex justify-center lg:justify-end">
            <div className="relative w-full max-w-lg">
              <Image
                src="/cartoon.jpg"
                alt="UstaadCart platform connecting vendors and suppliers"
                width={500}
                height={500}
                className="w-full h-auto rounded-2xl"
                priority
              />
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
