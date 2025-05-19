import { Search, Home, Radio, Zap, User, MoreVertical, Calendar, FileText, Plus } from "lucide-react"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"

export default function WorkspaceUI() {
  return (
    <div className="flex h-screen bg-slate-50">
      {/* Left Sidebar */}
      <div className="w-[220px] bg-white p-4 flex flex-col border-r">
        <div className="flex items-center gap-2 mb-6">
          <div className="w-8 h-8 rounded-full border flex items-center justify-center">
            <div className="w-5 h-5 rounded-full border border-gray-500"></div>
          </div>
          <span className="font-medium text-gray-800">Platform name</span>
        </div>

        <Button variant="outline" className="flex items-center gap-2 mb-6 bg-gray-50 justify-start">
          <Plus className="h-4 w-4" />
          <span>New chat</span>
        </Button>

        <nav className="space-y-1 flex-1">
          <Button variant="ghost" className="w-full justify-start">
            <Home className="mr-2 h-5 w-5 text-gray-500" />
            Home
          </Button>
          <Button variant="ghost" className="w-full justify-start">
            <Radio className="mr-2 h-5 w-5 text-gray-500" />
            Discover
          </Button>
          <Button variant="ghost" className="w-full justify-start bg-blue-50 text-blue-600">
            <Zap className="mr-2 h-5 w-5 text-blue-600" />
            Workspace
          </Button>
          <Button variant="ghost" className="w-full justify-start">
            <User className="mr-2 h-5 w-5 text-gray-500" />
            Profile
          </Button>
        </nav>
      </div>

      {/* Main Content */}
      <div className="flex-1 p-8 overflow-auto">
        <h1 className="text-3xl font-semibold text-purple-500 mb-6">Anjali's workspace</h1>

        {/* Tabs */}
        <div className="flex gap-4 mb-6">
          <div className="bg-white rounded-full px-4 py-2 flex items-center gap-2">
            <span>Chats</span>
            <Badge className="bg-blue-100 text-blue-800 hover:bg-blue-100">4</Badge>
          </div>
          <div className="bg-white rounded-full px-4 py-2 flex items-center gap-2">
            <span>Projects</span>
            <Badge className="bg-blue-100 text-blue-800 hover:bg-blue-100">5</Badge>
          </div>
          <div className="bg-white rounded-full px-4 py-2 flex items-center gap-2">
            <span>Templates</span>
            <Badge className="bg-blue-100 text-blue-800 hover:bg-blue-100">10</Badge>
          </div>
          <div className="bg-white rounded-full px-4 py-2 flex items-center gap-2">
            <span>Saved queries</span>
            <Badge className="bg-blue-100 text-blue-800 hover:bg-blue-100">6</Badge>
          </div>
        </div>

        {/* Search and New Chat */}
        <div className="flex justify-between mb-6">
          <div className="relative w-full max-w-md">
            <Input type="text" placeholder="Search chats" className="pl-4 pr-10 py-2 w-full bg-white" />
            <Search className="absolute right-3 top-2.5 h-5 w-5 text-gray-400" />
          </div>
          <Button className="flex items-center gap-2 bg-white text-gray-800 border hover:bg-gray-50">
            <Plus className="h-4 w-4" />
            <span>New chat</span>
          </Button>
        </div>

        {/* Chat Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {/* Card 1 */}
          <div className="bg-white rounded-lg p-5 border">
            <div className="flex justify-between mb-3">
              <Badge className="bg-green-100 text-green-800 hover:bg-green-100">GDP</Badge>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <MoreVertical className="h-5 w-5" />
              </Button>
            </div>
            <h3 className="font-medium text-lg mb-2">Name of the chat</h3>
            <p className="text-gray-600 text-sm mb-4">Short summary of the chat which will be two lines.</p>
            <div className="flex items-center text-gray-500 text-sm">
              <Calendar className="h-4 w-4 mr-2" />
              <span>12 March, 2025</span>
            </div>
          </div>

          {/* Card 2 */}
          <div className="bg-white rounded-lg p-5 border">
            <div className="flex justify-between mb-3">
              <Badge className="bg-blue-100 text-blue-800 hover:bg-blue-100">CPI</Badge>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <MoreVertical className="h-5 w-5" />
              </Button>
            </div>
            <h3 className="font-medium text-lg mb-2">Name of the chat</h3>
            <p className="text-gray-600 text-sm mb-4">Short summary of the chat which will be two lines.</p>
            <div className="flex items-center justify-between text-gray-500 text-sm">
              <div className="flex items-center">
                <Calendar className="h-4 w-4 mr-2" />
                <span>10 March, 2025</span>
              </div>
              <div className="relative">
                <FileText className="h-5 w-5" />
                <div className="absolute -top-1 -right-1 w-3 h-3 bg-blue-600 rounded-full"></div>
              </div>
            </div>
          </div>

          {/* Card 3 */}
          <div className="bg-white rounded-lg p-5 border">
            <div className="flex justify-between mb-3">
              <Badge className="bg-blue-100 text-blue-800 hover:bg-blue-100">CPI</Badge>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <MoreVertical className="h-5 w-5" />
              </Button>
            </div>
            <h3 className="font-medium text-lg mb-2">Name of the chat</h3>
            <p className="text-gray-600 text-sm mb-4">Short summary of the chat which will be two lines.</p>
            <div className="flex items-center justify-between text-gray-500 text-sm">
              <div className="flex items-center">
                <Calendar className="h-4 w-4 mr-2" />
                <span>09 March, 2025</span>
              </div>
              <FileText className="h-5 w-5" />
            </div>
          </div>

          {/* Card 4 */}
          <div className="bg-white rounded-lg p-5 border">
            <div className="flex justify-between mb-3">
              <Badge className="bg-green-100 text-green-800 hover:bg-green-100">GDP</Badge>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <MoreVertical className="h-5 w-5" />
              </Button>
            </div>
            <h3 className="font-medium text-lg mb-2">Name of the chat</h3>
            <p className="text-gray-600 text-sm mb-4">Short summary of the chat which will be two lines.</p>
            <div className="flex items-center text-gray-500 text-sm">
              <Calendar className="h-4 w-4 mr-2" />
              <span>08 March, 2025</span>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom User Bar */}
      <div className="fixed bottom-0 left-0 right-0 bg-white border-t p-2 flex justify-between items-center">
        <div className="flex items-center gap-2 ml-2">
          <Avatar className="h-8 w-8 border-2 border-blue-600">
            <AvatarImage src="/placeholder.svg?height=32&width=32" />
            <AvatarFallback>PA</AvatarFallback>
          </Avatar>
          <span className="font-medium text-blue-700">Pranav Aggarwal</span>
        </div>
        <Button variant="secondary" size="icon" className="mr-2">
          <Plus className="h-5 w-5" />
        </Button>
      </div>
    </div>
  )
}

