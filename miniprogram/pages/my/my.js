const app = getApp()

Page({
  data: {
    userInfo: null,
    stats: {
      totalBookings: 0,
      confirmedBookings: 0,
      completedBookings: 0
    }
  },

  onLoad: function () {
    this.loadUserInfo()
  },

  onShow: function () {
    this.loadUserInfo()
  },

  loadUserInfo: function () {
    const that = this
    const userInfo = wx.getStorageSync('userInfo')
    if (userInfo) {
      this.setData({
        userInfo: userInfo
      })
      this.loadStats()
      app.request({ url: '/user' }).then((data) => {
        const updated = Object.assign({}, userInfo, data)
        that.setData({ userInfo: updated })
        app.globalData.userInfo = updated
        wx.setStorageSync('userInfo', updated)
      }).catch(() => {})
    } else {
      wx.navigateTo({
        url: '/pages/login/login'
      })
    }
  },

  loadStats: function () {
    app.request({
      url: '/bookings'
    }).then((data) => {
      const stats = {
        totalBookings: data.length,
        confirmedBookings: data.filter(b => b.status === 'confirmed').length,
        completedBookings: data.filter(b => b.status === 'completed').length
      }
      this.setData({ stats })
    }).catch(() => {
      this.setData({
        stats: {
          totalBookings: 0,
          confirmedBookings: 0,
          completedBookings: 0
        }
      })
    })
  },

  goToBookings: function () {
    wx.navigateTo({
      url: '/pages/my-bookings/my-bookings'
    })
  },

  goToCoaches: function () {
    wx.switchTab({
      url: '/pages/coaches/coaches'
    })
  },

  goToLogin: function () {
    wx.navigateTo({
      url: '/pages/login/login'
    })
  },

  logout: function () {
    wx.showModal({
      title: '确认退出',
      content: '确定要退出登录吗？',
      success: (res) => {
        if (res.confirm) {
          app.globalData.token = null
          app.globalData.userInfo = null
          wx.removeStorageSync('token')
          wx.removeStorageSync('userInfo')
          this.setData({
            userInfo: null,
            stats: {
              totalBookings: 0,
              confirmedBookings: 0,
              completedBookings: 0
            }
          })
          wx.showToast({ title: '已退出', icon: 'success' })
          setTimeout(() => {
            wx.navigateTo({
              url: '/pages/login/login'
            })
          }, 1500)
        }
      }
    })
  }
})