// components/landingpage/navbar.tsx

"use client"

import { useState, useEffect } from "react"
import createClient from "@/lib/supabase/client"
import { useRouter } from "next/navigation"
import type { User, AuthChangeEvent, Session } from "@supabase/supabase-js"

import { Bell, Search, Settings, User as UserIcon, ChevronDown, LogOut } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
// REMOVED: No longer importing SidebarTrigger

export function Navbar() {
  const supabase = createClient()
  const router = useRouter()
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const fetchUser = async () => {
      const { data: { user } } = await supabase.auth.getUser()
      setUser(user)
      setIsLoading(false)
    }

    fetchUser()

    const { data: authListener } = supabase.auth.onAuthStateChange(
      (_event: AuthChangeEvent, session: Session | null) => {
        setUser(session?.user ?? null)
        console.log("user object", session?.user)
        console.log("session object", session)
        console.log("access token", session?.access_token)
      }
    )

    return () => {
      authListener?.subscription.unsubscribe()
    }
  }, [supabase, router])

  const handleSignOut = async () => {
    await supabase.auth.signOut()
    router.push('/sign-up')
    router.refresh()
  }
  
  const getInitials = (email: string | undefined) => {
      if (!email) return "U";
      return email.substring(0, 2).toUpperCase();
  }

  if (isLoading) {
    return (
      <nav className="sticky top-0 z-50 w-full border-b border-gray-200 bg-white/95">
        <div className="flex h-16 items-center justify-between px-4">
          <div className="flex-1"></div>
          <div className="h-8 w-24 rounded-md bg-gray-200 animate-pulse"></div>
        </div>
      </nav>
    )
  }

  return (
    <nav className="sticky top-0 z-50 w-full border-b bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/60">
      <div className="flex h-16 items-center justify-between px-4">
        <div className="flex flex-1 items-center gap-4">
          {/* REMOVED: The SidebarTrigger component is gone */}
         <h1>
            <span className="text-lg font-semibold text-red-600">RediMarket</span>
         </h1>
        </div>

        {/* Right Section */}
        <div className="flex items-center gap-3">
          {user ? (
        
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="h-9 gap-2 px-2 hover:bg-gray-100">
                  <Avatar className="h-7 w-7">
                    <AvatarImage src={user.user_metadata?.avatar_url} alt={user.user_metadata?.name || "User"} />
                    <AvatarFallback className="bg-[#e53935] text-xs font-bold text-white">
                      {getInitials(user.email)}
                    </AvatarFallback>
                  </Avatar>
                  <div className="hidden text-left sm:block">
                    <div className="text-sm font-medium">{user.user_metadata?.name || "User"}</div>
                    <div className="text-xs text-gray-500">{user.user_metadata?.role || "Subscriber"}</div>
                  </div>
                  <ChevronDown className="h-3 w-3 text-gray-400" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel>
                  <div className="flex flex-col space-y-1">
                    <p className="text-sm font-medium">{user.user_metadata?.name || "User"}</p>
                    <p className="text-xs text-gray-500">{user.email}</p>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem>
                  <UserIcon className="mr-2 h-4 w-4" />
                  <span>Profile</span>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleSignOut} className="cursor-pointer text-red-600 focus:text-red-600">
                  <LogOut className="mr-2 h-4 w-4" />
                  <span>Sign out</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <Button className="bg-red-600 hover:bg-red-400" onClick={() => router.push('/sign-in')}>
              Sign In
            </Button>
          )}
        </div>
      </div>
    </nav>
  )
}