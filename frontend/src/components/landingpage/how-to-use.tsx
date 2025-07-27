import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ShoppingCart, FileText, CreditCard, Truck, Building, Package, Bell, BarChart3, Users } from "lucide-react"

const vendorSteps = [
  {
    icon: FileText,
    title: "Sign up with your business details",
    description: "Quick registration with basic business information and mobile verification",
  },
  {
    icon: ShoppingCart,
    title: "Browse and compare products",
    description: "Access thousands of products from verified suppliers with transparent pricing",
  },
  {
    icon: Package,
    title: "Add to cart with bulk discounts",
    description: "See instant bulk pricing and save more as you order larger quantities",
  },
  {
    icon: CreditCard,
    title: "Pay instantly or use 'Pay Later'",
    description: "Flexible payment options including instant payment or credit for eligible vendors",
  },
  {
    icon: Truck,
    title: "Track orders and QR-verified delivery",
    description: "Real-time tracking with secure QR code verification at delivery",
  },
]

const supplierSteps = [
  {
    icon: Building,
    title: "Register with GST and documents",
    description: "Complete verification with GST details and company documentation",
  },
  {
    icon: Package,
    title: "Add products and set bulk pricing",
    description: "Upload product catalogs with images and configure tiered pricing structures",
  },
  {
    icon: Bell,
    title: "Receive orders and notifications",
    description: "Get instant notifications for new orders and customer inquiries",
  },
  {
    icon: BarChart3,
    title: "Manage orders from dashboard",
    description: "Comprehensive dashboard to track, fulfill, and manage all your orders",
  },
  {
    icon: Users,
    title: "Expand reach to hundreds of vendors",
    description: "Connect with verified street vendors and grow your business network",
  },
]

export default function HowToUseSection() {
  return (
    <section className="px-4 py-16 md:py-24 bg-gray-50">
      <div className="container mx-auto max-w-7xl">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold text-gray-900 mb-6">
            How does <span className="text-[#e53935]">UstaadCart</span> work?
          </h2>
          <p className="text-lg md:text-xl text-gray-600 max-w-3xl mx-auto">
            Simple steps to transform your business, whether you're a vendor looking for suppliers or a supplier wanting
            to reach more customers.
          </p>
        </div>

        <div className="grid lg:grid-cols-2 gap-8 lg:gap-12">
          {/* Vendors Card */}
          <Card className="border-2 border-gray-200 shadow-lg hover:shadow-xl transition-shadow duration-300">
            <CardHeader className="bg-[#e53935] text-white rounded-t-lg">
              <CardTitle className="text-2xl md:text-3xl font-bold text-center">For Vendors</CardTitle>
              <p className="text-center text-red-100 text-lg">Street vendors, small retailers, and local businesses</p>
            </CardHeader>
            <CardContent className="p-8">
              <div className="space-y-8">
                {vendorSteps.map((step, index) => (
                  <div key={index} className="flex gap-4">
                    <div className="flex-shrink-0">
                      <div className="w-12 h-12 bg-[#e53935] rounded-full flex items-center justify-center">
                        <step.icon className="w-6 h-6 text-white" />
                      </div>
                    </div>
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-gray-900 mb-2">
                        {index + 1}. {step.title}
                      </h3>
                      <p className="text-gray-600 leading-relaxed">{step.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Suppliers Card */}
          <Card className="border-2 border-gray-200 shadow-lg hover:shadow-xl transition-shadow duration-300">
            <CardHeader className="bg-[#d32f2f] text-white rounded-t-lg">
              <CardTitle className="text-2xl md:text-3xl font-bold text-center">For Suppliers</CardTitle>
              <p className="text-center text-red-100 text-lg">Wholesale suppliers, manufacturers, and distributors</p>
            </CardHeader>
            <CardContent className="p-8">
              <div className="space-y-8">
                {supplierSteps.map((step, index) => (
                  <div key={index} className="flex gap-4">
                    <div className="flex-shrink-0">
                      <div className="w-12 h-12 bg-[#d32f2f] rounded-full flex items-center justify-center">
                        <step.icon className="w-6 h-6 text-white" />
                      </div>
                    </div>
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-gray-900 mb-2">
                        {index + 1}. {step.title}
                      </h3>
                      <p className="text-gray-600 leading-relaxed">{step.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </section>
  )
}
